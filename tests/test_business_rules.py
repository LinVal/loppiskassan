"""Executable business rules for sales, settlement and payouts."""
import pytest
from conftest import sale
from v5_routes import payout_split, rate_bps
from fastapi import HTTPException

@pytest.mark.parametrize('gross,bps,fee,due', [
    (100,2500,25,75), (100,1000,10,90), (101,2500,25,76),
    (2,2500,1,1), (100,0,0,100), (100,10000,100,0),
])
def test_rounding_and_split(gross,bps,fee,due):
    assert payout_split(gross,bps) == (fee,due)
    assert fee + due == gross

@pytest.mark.parametrize('percent,bps', [(0,0),(10,1000),(25,2500),(100,10000),(12.345,1235)])
def test_rate_to_basis_points(percent,bps):
    assert rate_bps(percent)==bps

@pytest.mark.parametrize('bad',[-1,101])
def test_invalid_commission(bad):
    with pytest.raises(HTTPException): rate_bps(bad)

def test_25_percent_default_and_single_final_payout(client,seller,event):
    sid, response = sale(client)
    assert response.status_code == 200, response.text
    assert response.json()['total']==100
    settlement=client.get(f'/api/v5/events/{event}/settlement').json()
    assert settlement['totals']=={'gross':100,'commission':25,'due':75,'paid':0,'remaining':75}
    assert client.post(f'/api/v5/events/{event}/payouts/77',json={'actor':'Testledare'}).status_code==409
    assert client.post(f'/api/v5/events/{event}/close').status_code==200
    payout=client.post(f'/api/v5/events/{event}/payouts/77',json={'actor':'Testledare'})
    assert payout.status_code==201 and payout.json()['amount']==75
    assert client.post(f'/api/v5/events/{event}/payouts/77',json={'actor':'Testledare'}).status_code==409
    assert client.get(f'/api/v5/events/{event}/settlement').json()['totals']['remaining']==0
    assert client.post('/api/sessions',json={'register_no':'2'}).status_code==200
    _, after_close = sale(client)
    assert after_close.status_code==409

def test_commission_snapshot_not_recalculated(client,seller,event):
    assert client.put('/api/v5/sellers/77/commission',json={'rate':10}).status_code==200
    _, first=sale(client,price=100)
    assert first.status_code==200
    assert client.put('/api/v5/sellers/77/commission',json={'rate':50}).status_code==200
    _, second=sale(client,price=100)
    assert second.status_code==200
    totals=client.get(f'/api/v5/events/{event}/settlement').json()['totals']
    assert (totals['gross'],totals['commission'],totals['due'])==(200,60,140)

def test_payment_confirmation_and_idempotent_retry(client,seller,event):
    sid, rejected=sale(client,confirmed=False)
    assert rejected.status_code==400
    body={'items':[{'seller':'77','price':100}], 'method':'Swish','recipient':'Test','payment_confirmed':True}
    first=client.post(f'/api/sessions/{sid}/sale',json=body)
    second=client.post(f'/api/sessions/{sid}/sale',json=body)
    assert first.status_code==200 and second.status_code==200
    assert second.json()['already_saved'] is True
    assert first.json()['sale_id']==second.json()['sale_id']
    assert client.get(f'/api/v5/events/{event}/settlement').json()['totals']['gross']==100

def test_unknown_seller_does_not_create_sale(client,event):
    _, response=sale(client,seller='999')
    assert response.status_code==422
    assert client.get(f'/api/v5/events/{event}/settlement').json()['totals']['gross']==0

def test_adjustment_changes_settlement_and_closed_event_locks_it(client,seller,event):
    _, response=sale(client,price=100)
    sale_id=response.json()['sale_id']
    detail=client.get('/api/v4/sales').json()['sales']
    item_id=next(s['items'][0]['id'] for s in detail if s['id']==sale_id)
    adjustment={'sale_item_id':item_id,'amount':-20,'reason':'Prisjustering','actor':'Testledare'}
    assert client.post('/api/v4/adjustments',json=adjustment).status_code==201
    totals=client.get(f'/api/v5/events/{event}/settlement').json()['totals']
    assert (totals['gross'],totals['commission'],totals['due'])==(80,20,60)
    assert client.post(f'/api/v5/events/{event}/close').status_code==200
    assert client.post('/api/v4/adjustments',json=adjustment).status_code==409

def test_only_one_active_event(client,event):
    response=client.post('/api/v5/events',json={'name':'Samtidig loppis'})
    assert response.status_code==409

def test_utf8_password_and_health(client):
    assert client.get('/health').status_code==200
    assert client.get('/api/v5/events',headers={'Authorization':'Basic dGVzdGFyZTpmZWw='}).status_code==401
    assert client.get('/api/v5/events').status_code==200
