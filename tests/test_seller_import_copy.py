def create(client,name):
    r=client.post('/api/v5/events',json={'name':name});assert r.status_code==201;return r.json()['id']

def test_csv_import_and_reuse_staff(client):
    first=create(client,'Vår 2027')
    csv='nummer;namn;typ\n1;Anna;medarbetare\n72;Erik;extern\n'
    r=client.post(f'/api/v5/events/{first}/sellers/import',json={'content':csv})
    assert r.status_code==200,r.text
    assert r.json()['imported']==2
    assert client.post(f'/api/v5/events/{first}/start').status_code==200
    assert client.post(f'/api/v5/events/{first}/close').status_code==200
    second=create(client,'Höst 2027')
    r=client.post(f'/api/v5/events/{second}/sellers/copy',json={'source_event_id':first,'seller_type':'staff'})
    assert r.status_code==200,r.text
    assert r.json()['copied']==1
    assigned=client.get(f'/api/v5/events/{second}/sellers').json()['assigned']
    assert [(x['number'],x['name']) for x in assigned]==[('1','Anna')]

def test_import_atomic_duplicate_and_existing_conflict(client):
    eid=create(client,'Test import')
    duplicate='nummer;namn\n12;Anna\n12;Erik\n'
    assert client.post(f'/api/v5/events/{eid}/sellers/import',json={'content':duplicate}).status_code==422
    assert client.get(f'/api/v5/events/{eid}/sellers').json()['assigned']==[]
    good='nummer;namn\n12;Anna\n'
    assert client.post(f'/api/v5/events/{eid}/sellers/import',json={'content':good}).status_code==200
    r=client.post(f'/api/v5/events/{eid}/sellers/import',json={'content':'nummer;namn\n13;Erik\n12;Nytt namn\n'})
    assert r.status_code==409
    assert len(client.get(f'/api/v5/events/{eid}/sellers').json()['assigned'])==1

def test_import_only_draft_and_bad_values(client):
    eid=create(client,'Importvalidering')
    for csv in ('nummer;namn\n251;Anna\n','nummer;namn\n1; \n','nummer;namn;typ\n1;Anna;okänd\n'):
        assert client.post(f'/api/v5/events/{eid}/sellers/import',json={'content':csv}).status_code==422
    assert client.post(f'/api/v5/events/{eid}/sellers/import',json={'content':'nummer;namn\n1;Anna\n'}).status_code==200
    assert client.post(f'/api/v5/events/{eid}/start').status_code==200
    assert client.post(f'/api/v5/events/{eid}/sellers/import',json={'content':'nummer;namn\n2;Bo\n'}).status_code==409
