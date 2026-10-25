"""Roles, account isolation, and 10 simultaneous cashiers on disposable DB."""
import base64
from concurrent.futures import ThreadPoolExecutor
from conftest import sale

def basic(username, password):
    return {'Authorization':'Basic '+base64.b64encode(f'{username}:{password}'.encode()).decode()}

def test_staff_permissions_and_audit(client,seller,event):
    created=client.post('/api/staff',json={'username':'kassa1','password':'starkt-lösenord-123','role':'cashier'})
    assert created.status_code==201,created.text
    headers=basic('kassa1','starkt-lösenord-123')
    assert client.get('/api/staff',headers=headers).status_code==403
    assert client.put('/api/v5/sellers/77/commission',json={'rate':0},headers=headers).status_code==403
    assert client.post(f'/api/v5/events/{event}/close',headers=headers).status_code==403
    assert client.post('/api/sessions',json={'register_no':'1'},headers=headers).status_code==200
    assert client.post('/api/staff/kassa1/disable').status_code==200
    assert client.post('/api/sessions',json={'register_no':'1'},headers=headers).status_code==401
    audit=client.get('/api/staff/audit').json()['events']
    assert any(x['actor']=='kassa1' and x['path']=='/api/sessions' for x in audit)

def test_ten_concurrent_registers(client,seller,event):
    def register(i):
        sid=client.post('/api/sessions',json={'register_no':str(i)}).json()['session_id']
        response=client.post(f'/api/sessions/{sid}/sale',json={'items':[{'seller':'77','price':100}], 'method':'Swish','recipient':'Test','payment_confirmed':True})
        return response.status_code, response.json()
    with ThreadPoolExecutor(max_workers=10) as pool:
        results=list(pool.map(register,range(1,11)))
    assert all(status==200 for status,_ in results),results
    assert len({body['sale_id'] for _,body in results})==10
    assert client.get(f'/api/v5/events/{event}/settlement').json()['totals']['gross']==1000
