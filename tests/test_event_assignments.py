"""Event seller assignment, start gate and immutable sale ownership."""
def test_draft_start_and_available_numbers(client):
    r=client.post('/api/v5/events',json={'name':'Vårmarknad'})
    assert r.status_code==201
    eid=r.json()['id']
    assert r.json()['status']=='draft'
    assert client.post(f'/api/v5/events/{eid}/start').status_code==409
    assert client.put(f'/api/v5/events/{eid}/sellers',json={'number':12,'name':'  ','seller_type':'staff'}).status_code==422
    assert client.put(f'/api/v5/events/{eid}/sellers',json={'number':12,'name':'Kim','seller_type':'staff'}).status_code==200
    assert client.put(f'/api/v5/events/{eid}/sellers',json={'number':230,'name':'Lo','seller_type':'external'}).status_code==200
    assert client.get(f'/api/v5/events/{eid}/sellers').json()['available']==248
    assert client.post(f'/api/v5/events/{eid}/start').json()['assigned']==2

def test_unassigned_number_rejected_and_used_owner_locked(client,seller):
    eid=client.post('/api/v5/events',json={'name':'Höstmarknad'}).json()['id']
    assert client.put(f'/api/v5/events/{eid}/sellers',json={'number':77,'name':'Testsäljare'}).status_code==200
    assert client.post(f'/api/v5/events/{eid}/start').status_code==200
    sid=client.post('/api/sessions',json={'register_no':'1'}).json()['session_id']
    payload={'items':[{'seller':'78','price':25}],'method':'Swish','recipient':'Test','payment_confirmed':True}
    assert client.post(f'/api/sessions/{sid}/sale',json=payload).status_code==422
    payload['items'][0]['seller']='77'
    assert client.post(f'/api/sessions/{sid}/sale',json=payload).status_code==200
    assert client.put(f'/api/v5/events/{eid}/sellers',json={'number':77,'name':'Någon annan'}).status_code==409
    assert client.delete(f'/api/v5/events/{eid}/sellers/77').status_code==409

def test_free_number_can_be_released_before_start(client):
    eid=client.post('/api/v5/events',json={'name':'Förberedelse'}).json()['id']
    assert client.put(f'/api/v5/events/{eid}/sellers',json={'number':1,'name':'En medarbetare','seller_type':'staff'}).status_code==200
    assert client.delete(f'/api/v5/events/{eid}/sellers/1').status_code==200
    assert client.get(f'/api/v5/events/{eid}/sellers').json()['available']==250
