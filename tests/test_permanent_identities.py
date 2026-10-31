def test_copy_preserves_identity(client):
    first=client.post('/api/v5/events',json={'name':'Identitet vår'}).json()['id']
    r=client.put(f'/api/v5/events/{first}/sellers',json={'number':11,'name':'Anna','seller_type':'staff'})
    assert r.status_code==200,r.text
    original=client.get(f'/api/v5/events/{first}/sellers').json()['assigned'][0]['identity_id']
    second=client.post('/api/v5/events',json={'name':'Identitet höst'}).json()['id']
    r=client.post(f'/api/v5/events/{second}/sellers/copy',json={'source_event_id':first})
    assert r.status_code==200,r.text
    copied=client.get(f'/api/v5/events/{second}/sellers').json()['assigned'][0]['identity_id']
    assert original==copied
    assert client.get('/api/v5/seller-identities').status_code==200

def test_same_name_not_merged(client):
    eid=client.post('/api/v5/events',json={'name':'Två med samma namn'}).json()['id']
    for n in (41,42):
        r=client.put(f'/api/v5/events/{eid}/sellers',json={'number':n,'name':'Anna'})
        assert r.status_code==200,r.text
    rows=client.get(f'/api/v5/events/{eid}/sellers').json()['assigned']
    assert len({r['identity_id'] for r in rows})==2

def test_unknown_identity_rejected(client):
    eid=client.post('/api/v5/events',json={'name':'Okänt ID'}).json()['id']
    r=client.put(f'/api/v5/events/{eid}/sellers',json={'number':15,'name':'Anna','identity_id':'missing'})
    assert r.status_code==422
