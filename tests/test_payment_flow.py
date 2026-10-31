from conftest import sale

def test_payment_methods_and_cash_rules(client, seller, event):
    for method, cash, expected in [('Swish',None,200),('Kort',None,200),('Kontant',100,200),('Kontant',95,400),('Annat',None,422)]:
        sid=client.post('/api/sessions',json={'register_no':'1'}).json()['session_id']
        body={'items':[{'seller':seller,'price':100}], 'method':method,'recipient':'Kassa 1','payment_confirmed':True}
        if cash is not None: body['cash_received']=cash
        r=client.post(f'/api/sessions/{sid}/sale',json=body)
        assert r.status_code==expected, r.text

def test_cash_requires_amount(client,seller,event):
    sid=client.post('/api/sessions',json={'register_no':'1'}).json()['session_id']
    body={'items':[{'seller':seller,'price':100}], 'method':'Kontant','recipient':'Kassa 1','payment_confirmed':True}
    assert client.post(f'/api/sessions/{sid}/sale',json=body).status_code==400
    body['cash_received']=120
    assert client.post(f'/api/sessions/{sid}/sale',json=body).status_code==200
    assert client.post(f'/api/sessions/{sid}/sale',json=body).json()['already_saved'] is True
