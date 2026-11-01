import uuid

def test_qr_scanning_and_validation(client):
    sid=client.post('/api/sessions',json={'register_no':'1'}).json()['session_id']
    link=client.post(f'/api/sessions/{sid}/pair').json()['url']
    token=link.split('token=')[1]
    scan_id=str(uuid.uuid4())
    endpoint=f'/api/mobile/{token}/qr'
    payload={'scan_id':scan_id,'payload':'LK1|77|50|Troja'}
    assert client.post(endpoint,json=payload).status_code==200
    assert client.post(endpoint,json=payload).json()['status']=='already_received'
    scans=client.get(f'/api/sessions/{sid}/qr-scans').json()['scans']
    assert len(scans)==1 and scans[0]['seller']=='77' and scans[0]['price']==50
    assert client.post(endpoint,json={'scan_id':str(uuid.uuid4()),'payload':'LK1|77|52|Fel'}).status_code==422
    assert client.post(endpoint,json={'scan_id':str(uuid.uuid4()),'payload':'https://example.com'}).status_code==422
    assert client.post('/api/mobile/invalid/qr',json=payload).status_code==403
