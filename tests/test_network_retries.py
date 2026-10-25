"""Network retry and duplicate submission tests; use isolated SQLite test DB."""
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import text


def test_retry_after_lost_response_returns_same_sale(client, seller, event):
    """Simulate server committing, but cashier losing the HTTP response."""
    session = client.post('/api/sessions', json={'register_no': '3'}).json()['session_id']
    payload = {'items': [{'seller': seller, 'price': 125}],
               'method': 'Swish', 'recipient': 'Test', 'payment_confirmed': True}
    first = client.post(f'/api/sessions/{session}/sale', json=payload)
    assert first.status_code == 200, first.text
    # Client ignores the first response (simulated lost connection) and retries.
    second = client.post(f'/api/sessions/{session}/sale', json=payload)
    assert second.status_code == 200, second.text
    assert second.json()['sale_id'] == first.json()['sale_id']
    assert second.json()['already_saved'] is True
    from server import engine
    with engine.connect() as db:
        count = db.execute(text('SELECT COUNT(*) FROM sales WHERE session_id=:sid'),
                           {'sid': session}).scalar_one()
        items = db.execute(text('SELECT COUNT(*) FROM sale_items WHERE sale_id=:sale'),
                           {'sale': first.json()['sale_id']}).scalar_one()
    assert count == 1
    assert items == 1


def test_repeated_retry_never_adds_more_items(client, seller, event):
    session = client.post('/api/sessions', json={'register_no': '4'}).json()['session_id']
    payload = {'items': [{'seller': seller, 'price': 75},
                         {'seller': seller, 'price': 25}],
               'method': 'Swish', 'recipient': 'Test', 'payment_confirmed': True}
    responses = [client.post(f'/api/sessions/{session}/sale', json=payload) for _ in range(6)]
    assert all(r.status_code == 200 for r in responses)
    assert len({r.json()['sale_id'] for r in responses}) == 1
    assert [r.json()['already_saved'] for r in responses] == [False] + [True] * 5
    from server import engine
    with engine.connect() as db:
        total, count = db.execute(text(
            'SELECT COALESCE(SUM(price),0), COUNT(*) FROM sale_items WHERE sale_id=:id'
        ), {'id': responses[0].json()['sale_id']}).one()
    assert (total, count) == (100, 2)
