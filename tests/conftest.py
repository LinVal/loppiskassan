"""Each test suite uses an isolated, disposable SQLite database; never Heroku."""
import base64
import importlib
import os
import sys
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{tmp_path / "test.db"}')
    monkeypatch.setenv('DEMO_USER', 'testare')
    monkeypatch.setenv('DEMO_PASSWORD', 'lösenord-åäö-12345')
    monkeypatch.delenv('S3_BUCKET', raising=False)
    monkeypatch.delenv('BUCKETEER_BUCKET_NAME', raising=False)
    for name in ('server', 'sellers', 'events', 'staff_auth'):
        sys.modules.pop(name, None)
    app = importlib.import_module('server').app
    with TestClient(app) as c:
        credentials=base64.b64encode('testare:lösenord-åäö-12345'.encode()).decode()
        c.headers.update({'Authorization': 'Basic '+credentials})
        yield c
    for name in ('server', 'sellers', 'events', 'staff_auth'):
        sys.modules.pop(name, None)

@pytest.fixture
def seller(client):
    response = client.post('/api/v4/sellers', json={'number':'77','name':'Testsäljare'})
    assert response.status_code == 201, response.text
    return '77'

@pytest.fixture
def event(client):
    response = client.post('/api/v5/events', json={'name':'Testloppis'})
    assert response.status_code == 201, response.text
    return response.json()['id']

def sale(client, seller='77', price=100, register='1', confirmed=True):
    session = client.post('/api/sessions', json={'register_no':register}).json()['session_id']
    response = client.post(f'/api/sessions/{session}/sale', json={
        'items':[{'seller':seller,'price':price}],
        'method':'Swish', 'recipient':'Test', 'payment_confirmed':confirmed,
    })
    return session, response
