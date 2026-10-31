def test_search_history_and_reuse(client):
    first=client.post('/api/v5/events',json={'name':'Sök vår'}).json()['id']
    assert client.put(f'/api/v5/events/{first}/sellers',json={'number':18,'name':'Sökbar Person','seller_type':'staff'}).status_code==200
    identity=client.get(f'/api/v5/events/{first}/sellers').json()['assigned'][0]['identity_id']
    found=client.get('/api/v5/seller-identities',params={'q':'sökbar'}).json()['sellers']
    assert any(x['id']==identity for x in found)
    history=client.get(f'/api/v5/seller-identities/{identity}/history').json()
    assert any(x['event_id']==first and x['number']=='18' for x in history['events'])
    second=client.post('/api/v5/events',json={'name':'Sök höst'}).json()['id']
    assert client.put(f'/api/v5/events/{second}/sellers',json={'number':77,'name':'Sökbar Person','seller_type':'staff','identity_id':identity}).status_code==200
    history=client.get(f'/api/v5/seller-identities/{identity}/history').json()
    assert {x['number'] for x in history['events']}=={'18','77'}


def test_unknown_history_and_bad_search(client):
    assert client.get('/api/v5/seller-identities/does-not-exist/history').status_code==404
    assert client.get('/api/v5/seller-identities',params={'limit':999}).status_code==422
