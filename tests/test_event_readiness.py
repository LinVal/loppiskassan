def test_readiness_allows_unassigned_numbers(client):
    eid=client.post('/api/v5/events',json={'name':'Förberedelse'}).json()['id']
    url=f'/api/v5/events/{eid}/readiness'
    before=client.get(url).json()
    assert before['ready'] is False and before['assigned']==0
    assert client.post(f'/api/v5/events/{eid}/start').status_code==409
    assert client.put(f'/api/v5/events/{eid}/sellers',json={'number':3,'name':'Anna','seller_type':'staff'}).status_code==200
    assert client.put(f'/api/v5/events/{eid}/sellers',json={'number':91,'name':'Bo','seller_type':'external'}).status_code==200
    ready=client.get(url).json()
    assert ready['ready'] and ready['assigned']==2 and ready['staff']==1 and ready['external']==1 and ready['available']==248
    assert client.post(f'/api/v5/events/{eid}/start').status_code==200
    assert client.get(url).json()['ready'] is False


def test_same_identity_cannot_get_two_numbers(client):
    eid=client.post('/api/v5/events',json={'name':'Ingen dubblett'}).json()['id']
    assert client.put(f'/api/v5/events/{eid}/sellers',json={'number':10,'name':'Anna'}).status_code==200
    identity=client.get(f'/api/v5/events/{eid}/sellers').json()['assigned'][0]['identity_id']
    response=client.put(f'/api/v5/events/{eid}/sellers',json={'number':11,'name':'Anna','identity_id':identity})
    assert response.status_code==409
    assert client.get(f'/api/v5/events/{eid}/readiness').json()['assigned']==1
