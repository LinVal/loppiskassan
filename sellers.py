"""V4 seller registry, read-only portal, auditable corrections and reports."""
import csv, io, secrets, hashlib, datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

router=APIRouter()
engine=None

def install(db_engine):
    global engine
    engine=db_engine
    # One-off DDL on app startup; serialize on PostgreSQL to avoid simultaneous dyno startup DDL.
    with engine.begin() as db:
        if engine.dialect.name=='postgresql': db.execute(text('SELECT pg_advisory_xact_lock(87420014)'))
        db.execute(text('CREATE TABLE IF NOT EXISTS sellers (number VARCHAR(4) PRIMARY KEY, name VARCHAR(150) NOT NULL, email VARCHAR(200) NOT NULL DEFAULT \'\', phone VARCHAR(40) NOT NULL DEFAULT \'\', active INTEGER NOT NULL DEFAULT 1, portal_token_hash VARCHAR(64), created_at VARCHAR(40) NOT NULL)'))
        db.execute(text('CREATE TABLE IF NOT EXISTS adjustments (id VARCHAR(64) PRIMARY KEY, sale_item_id VARCHAR(64) NOT NULL, sale_id VARCHAR(64) NOT NULL, seller VARCHAR(4) NOT NULL, amount INTEGER NOT NULL, reason VARCHAR(250) NOT NULL, actor VARCHAR(100) NOT NULL, created_at VARCHAR(40) NOT NULL)'))

def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def seller_no(n):
    if not n.isascii() or not n.isdigit() or not 1<=len(n)<=4: raise HTTPException(422,'Säljnummer måste vara 1–4 siffror')
    return n

class SellerIn(BaseModel):
    number:str=Field(min_length=1,max_length=4)
    name:str=Field(min_length=1,max_length=150)
    email:str=Field(default='',max_length=200)
    phone:str=Field(default='',max_length=40)
    active:bool=True

@router.get('/api/v4/sellers')
def list_sellers():
    with engine.connect() as db:
        rows=db.execute(text('SELECT number,name,email,phone,active,created_at FROM sellers ORDER BY LENGTH(number),number')).mappings().all()
    return {'sellers':[dict(r) for r in rows]}

@router.post('/api/v4/sellers',status_code=201)
def add_seller(s:SellerIn):
    number=seller_no(s.number)
    with engine.begin() as db:
        if db.execute(text('SELECT 1 FROM sellers WHERE number=:n'),{'n':number}).first():raise HTTPException(409,'Säljnumret finns redan')
        db.execute(text('INSERT INTO sellers (number,name,email,phone,active,created_at) VALUES (:n,:name,:email,:phone,:active,:created)'),{'n':number,'name':s.name,'email':s.email,'phone':s.phone,'active':int(s.active),'created':stamp()})
    return {'number':number}

@router.put('/api/v4/sellers/{number}')
def update_seller(number:str,s:SellerIn):
    seller_no(number)
    if s.number!=number:raise HTTPException(400,'Säljnummer kan inte ändras')
    with engine.begin() as db:
        result=db.execute(text('UPDATE sellers SET name=:name,email=:email,phone=:phone,active=:active WHERE number=:n'),{'n':number,'name':s.name,'email':s.email,'phone':s.phone,'active':int(s.active)})
        if not result.rowcount:raise HTTPException(404,'Säljare saknas')
    return {'ok':True}

@router.post('/api/v4/sellers/{number}/portal-link')
def portal_link(number:str,request:Request):
    seller_no(number)
    token=secrets.token_urlsafe(32)
    hashed=hashlib.sha256(token.encode()).hexdigest()
    with engine.begin() as db:
        result=db.execute(text('UPDATE sellers SET portal_token_hash=:h WHERE number=:n AND active=1'),{'h':hashed,'n':number})
        if not result.rowcount:raise HTTPException(404,'Aktiv säljare saknas')
    # Only returned once; generating a new link revokes the old one.
    import os
    base=os.getenv('PUBLIC_BASE_URL','').rstrip('/') or str(request.base_url).rstrip('/')
    return {'url':f'{base}/seller?token={token}','note':'Länken ger åtkomst till säljarens försäljning. Dela privat. Ny länk spärrar den gamla.'}

@router.get('/seller')
def seller_page():
    from pathlib import Path
    return FileResponse(Path(__file__).parent/'static'/'seller.html')

@router.get('/api/portal/{token}')
def portal_data(token:str):
    if len(token)>128 or len(token)<20:raise HTTPException(404,'Ogiltig länk')
    hashed=hashlib.sha256(token.encode()).hexdigest()
    with engine.connect() as db:
        seller=db.execute(text('SELECT number,name FROM sellers WHERE portal_token_hash=:h AND active=1'),{'h':hashed}).mappings().first()
        if not seller:raise HTTPException(404,'Länken är ogiltig eller återkallad')
        items=db.execute(text('''SELECT si.id,si.description,si.price,sa.created_at,sa.register_no,sa.id AS sale_id,
          COALESCE((SELECT SUM(a.amount) FROM adjustments a WHERE a.sale_item_id=si.id),0) AS correction
          FROM sale_items si JOIN sales sa ON sa.id=si.sale_id WHERE si.seller=:n ORDER BY sa.created_at DESC'''),{'n':seller['number']}).mappings().all()
    return {'seller':dict(seller),'items':[dict(x) for x in items],'total':sum(x['price']+x['correction'] for x in items)}

@router.get('/api/v4/sales')
def sales_detail(limit:int=100,offset:int=0):
    limit=max(1,min(limit,250));offset=max(0,offset)
    with engine.connect() as db:
        sales=db.execute(text('SELECT id,session_id,register_no,total,method,recipient,created_at FROM sales ORDER BY created_at DESC LIMIT :l OFFSET :o'),{'l':limit,'o':offset}).mappings().all()
        ids=[x['id'] for x in sales]
        result=[]
        for sale in sales:
            rows=db.execute(text('''SELECT si.id,si.seller,si.description,si.price,COALESCE((SELECT SUM(amount) FROM adjustments WHERE sale_item_id=si.id),0) AS correction FROM sale_items si WHERE sale_id=:id'''),{'id':sale['id']}).mappings().all()
            itemlist=[dict(x) for x in rows]
            photos=db.execute(text('SELECT id,created_at FROM photos WHERE session_id=:sid ORDER BY created_at'),{'sid':sale['session_id']}).mappings().all()
            result.append({**dict(sale),'items':itemlist,'photos':[{'id':r['id'],'created_at':r['created_at'],'url':f'/api/sessions/{sale["session_id"]}/photos/{r["id"]}'} for r in photos],'net_total':sum(x['price']+x['correction'] for x in itemlist)})
    return {'sales':result,'limit':limit,'offset':offset}

class Adjustment(BaseModel):
    sale_item_id:str
    amount:int=Field(ge=-1000000,le=1000000)
    reason:str=Field(min_length=5,max_length=250)
    actor:str=Field(min_length=2,max_length=100)

@router.post('/api/v4/adjustments',status_code=201)
def add_adjustment(a:Adjustment):
    import uuid
    if a.amount==0:raise HTTPException(422,'Ändringen får inte vara noll')
    with engine.begin() as db:
        item=db.execute(text('SELECT si.id,si.sale_id,si.seller,si.price,sa.event_id FROM sale_items si JOIN sales sa ON sa.id=si.sale_id WHERE si.id=:id'),{'id':a.sale_item_id}).mappings().first()
        if not item:raise HTTPException(404,'Varurad saknas')
        from events import require_event_open
        require_event_open(db,item['event_id'])
        previous=db.execute(text('SELECT COALESCE(SUM(amount),0) FROM adjustments WHERE sale_item_id=:id'),{'id':a.sale_item_id}).scalar_one()
        if item['price']+previous+a.amount<0:raise HTTPException(422,'Radens netto får inte bli negativt')
        aid=str(uuid.uuid4())
        db.execute(text('INSERT INTO adjustments (id,sale_item_id,sale_id,seller,amount,reason,actor,created_at) VALUES (:id,:iid,:sid,:seller,:amount,:reason,:actor,:created)'),{'id':aid,'iid':item['id'],'sid':item['sale_id'],'seller':item['seller'],'amount':a.amount,'reason':a.reason,'actor':a.actor,'created':stamp()})
    return {'id':aid,'net_item_price':item['price']+previous+a.amount,'note':'Bokföringsjustering registrerad; ingen automatisk återbetalning har gjorts.'}

@router.get('/api/v4/adjustments')
def audit_log():
    with engine.connect() as db:
        rows=db.execute(text('SELECT * FROM adjustments ORDER BY created_at DESC LIMIT 500')).mappings().all()
    return {'adjustments':[dict(x) for x in rows]}

@router.get('/api/v4/reports')
def reports():
    with engine.connect() as db:
        sellers=db.execute(text('''SELECT si.seller,COUNT(*) AS items,SUM(si.price) AS gross,
          COALESCE((SELECT SUM(a.amount) FROM adjustments a WHERE a.seller=si.seller),0) AS corrections
          FROM sale_items si GROUP BY si.seller ORDER BY si.seller''')).mappings().all()
        registers=db.execute(text('''SELECT sa.register_no,sa.method,COUNT(DISTINCT sa.id) AS sales_count,SUM(si.price) AS gross,
          COALESCE((SELECT SUM(a.amount) FROM adjustments a JOIN sales s2 ON s2.id=a.sale_id WHERE s2.register_no=sa.register_no AND s2.method=sa.method),0) AS corrections
          FROM sales sa JOIN sale_items si ON si.sale_id=sa.id GROUP BY sa.register_no,sa.method ORDER BY sa.register_no,sa.method''')).mappings().all()
        days=db.execute(text('''SELECT SUBSTR(sa.created_at,1,10) AS day,COUNT(DISTINCT sa.id) AS sales_count,SUM(si.price) AS gross,
          COALESCE((SELECT SUM(a.amount) FROM adjustments a WHERE SUBSTR(a.created_at,1,10)=SUBSTR(sa.created_at,1,10)),0) AS corrections
          FROM sales sa JOIN sale_items si ON si.sale_id=sa.id GROUP BY SUBSTR(sa.created_at,1,10) ORDER BY day DESC''')).mappings().all()
    return {'sellers':[dict(x,net=x['gross']+x['corrections']) for x in sellers],
            'registers':[dict(x,net=x['gross']+x['corrections']) for x in registers],
            'days':[dict(x) for x in days],
            'note':'Dagsrapportens korrigeringar visas efter korrigeringsdatum (UTC). Kassasummering är bokförd försäljning, inte avstämd betalning.'}

@router.get('/api/v4/reports/sellers.csv')
def report_csv():
    data=reports()['sellers'];output=io.StringIO();output.write('\ufeff')
    writer=csv.writer(output,delimiter=';');writer.writerow(['Säljnummer','Antal varor','Brutto kr','Korrigering kr','Netto kr'])
    for row in data:writer.writerow([row['seller'],row['items'],row['gross'],row['corrections'],row['net']])
    return StreamingResponse(iter([output.getvalue().encode('utf-8')]),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="saljarredovisning.csv"'})

@router.get('/admin')
def admin_page():
    from pathlib import Path
    return FileResponse(Path(__file__).parent/'static'/'admin.html')
