"""PostgreSQL integration: 10 concurrent registers, 100 sales each.

Run only against an explicitly named disposable database, never Heroku.
"""
import base64
import importlib
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

PG_URL = os.getenv('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.postgres


def test_ten_registers_thousand_sales_postgres(monkeypatch):
    if not PG_URL:
        pytest.skip('Set TEST_DATABASE_URL to an isolated disposable PostgreSQL database')
    if not PG_URL.startswith(('postgresql://', 'postgresql+psycopg://')):
        pytest.fail('TEST_DATABASE_URL must point to PostgreSQL')
    if os.getenv('DATABASE_URL') and PG_URL == os.getenv('DATABASE_URL'):
        pytest.fail('Refusing to test against DATABASE_URL')
    if any(host in PG_URL.lower() for host in ('heroku', 'amazonaws.com', 'rds.amazonaws')):
        pytest.fail('Refusing a remote/production-like PostgreSQL URL')
    if not any(host in PG_URL.lower() for host in ('localhost', '127.0.0.1', '@postgres:', '@db:')):
        pytest.fail('Only local or CI PostgreSQL is permitted')

    monkeypatch.setenv('DATABASE_URL', PG_URL)
    monkeypatch.setenv('DEMO_USER', 'testadmin')
    monkeypatch.setenv('DEMO_PASSWORD', 'temporary-test-password-123')
    monkeypatch.delenv('BUCKETEER_BUCKET_NAME', raising=False)
    monkeypatch.delenv('S3_BUCKET', raising=False)
    for name in ('server', 'v4_routes', 'v5_routes', 'staff_auth'):
        sys.modules.pop(name, None)

    server = importlib.import_module('server')
    auth = base64.b64encode(b'testadmin:temporary-test-password-123').decode()
    headers = {'Authorization': 'Basic ' + auth}
    try:
        with TestClient(server.app) as client:
            client.headers.update(headers)
            seller = client.post('/api/v4/sellers', json={'number': '77', 'name': 'Belastningstest'})
            assert seller.status_code == 201, seller.text
            event_response = client.post('/api/v5/events', json={'name': 'PG belastningstest'})
            assert event_response.status_code == 201, event_response.text
            event_id = event_response.json()['id']

            def register_worker(register_no):
                # Each thread represents one cash register, sending 100 sales in sequence.
                # Separate clients avoid sharing mutable HTTP client state between threads.
                with TestClient(server.app, headers=headers) as cashier:
                    results = []
                    for i in range(100):
                        session_response = cashier.post('/api/sessions', json={'register_no': str(register_no)})
                        assert session_response.status_code == 200, session_response.text
                        session_id = session_response.json()['session_id']
                        payload = {'items': [{'seller': '77', 'price': 100}],
                                   'method': 'Swish', 'recipient': 'Test', 'payment_confirmed': True}
                        response = cashier.post(f'/api/sessions/{session_id}/sale', json=payload)
                        assert response.status_code == 200, response.text
                        data = response.json()
                        assert data['total'] == 100 and data['already_saved'] is False
                        results.append((session_id, data['sale_id'], register_no))
                    return results

            with ThreadPoolExecutor(max_workers=10) as executor:
                batches = list(executor.map(register_worker, range(1, 11)))
            results = [sale for batch in batches for sale in batch]
            assert len(results) == 1000
            assert len({sid for sid, _, _ in results}) == 1000
            assert len({sale_id for _, sale_id, _ in results}) == 1000
            assert Counter(register for _, _, register in results) == {i: 100 for i in range(1, 11)}

            # Check the database itself (the /api/sales listing is limited to 200 rows).
            with server.engine.connect() as db:
                row = db.execute(text('''SELECT COUNT(*) AS sales, SUM(total) AS gross,
                    COUNT(DISTINCT session_id) AS sessions
                    FROM sales WHERE event_id=:event'''), {'event': event_id}).mappings().one()
                assert dict(row) == {'sales': 1000, 'gross': 100000, 'sessions': 1000}
                registers = db.execute(text('''SELECT register_no, COUNT(*) AS n FROM sales
                    WHERE event_id=:event GROUP BY register_no'''), {'event': event_id}).all()
                assert {int(r[0]): r[1] for r in registers} == {i: 100 for i in range(1, 11)}
                items = db.execute(text('''SELECT COUNT(*), SUM(si.price), MIN(si.commission_bps),
                    MAX(si.commission_bps) FROM sale_items si
                    JOIN sales s ON s.id=si.sale_id WHERE s.event_id=:event'''), {'event': event_id}).one()
                assert tuple(items) == (1000, 100000, 2500, 2500)

            settlement = client.get(f'/api/v5/events/{event_id}/settlement')
            assert settlement.status_code == 200, settlement.text
            totals = settlement.json()['totals']
            assert (totals['gross'], totals['commission'], totals['due']) == (100000, 25000, 75000)

            # Idempotency: two simultaneous attempts to save one session -> one sale.
            session_id = client.post('/api/sessions', json={'register_no': '1'}).json()['session_id']
            payload = {'items': [{'seller': '77', 'price': 100}], 'method': 'Swish',
                       'recipient': 'Test', 'payment_confirmed': True}
            def duplicate_attempt(_):
                with TestClient(server.app, headers=headers) as cashier:
                    r = cashier.post(f'/api/sessions/{session_id}/sale', json=payload)
                    assert r.status_code == 200, r.text
                    return r.json()
            with ThreadPoolExecutor(max_workers=2) as executor:
                duplicate_results = list(executor.map(duplicate_attempt, range(2)))
            assert duplicate_results[0]['sale_id'] == duplicate_results[1]['sale_id']
            assert sorted(x['already_saved'] for x in duplicate_results) == [False, True]
            with server.engine.connect() as db:
                assert db.execute(text('SELECT COUNT(*) FROM sales WHERE session_id=:s'), {'s': session_id}).scalar_one() == 1
    finally:
        server.engine.dispose()
        for name in ('server', 'v4_routes', 'v5_routes', 'staff_auth'):
            sys.modules.pop(name, None)
