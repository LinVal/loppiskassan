"""Event-specific settlement, commission snapshots and manual payout ledger (v5)."""
import csv, io, uuid, datetime
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

router=APIRouter(); engine=None

def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def rate_bps(rate):
    if not 0 <= rate <= 100: raise HTTPException(422,'Provision måste vara 0–100 %')
    return int((Decimal(str(rate))*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
def payout_split(gross,bps):
    fee=int((Decimal(gross)*Decimal(bps)/Decimal(10000)).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    return fee,gross-fee

def install(e):
    global engine; engine=e
    with engine.begin() as db:
        if engine.dialect.name=='postgresql':db.execute(text('SELECT pg_advisory_xact_lock(87420015)'))
        db.execute(text("CREATE TABLE IF NOT EXISTS flea_events (id VARCHAR(64) PRIMARY KEY, name VARCHAR(150) NOT NULL, status VARCHAR(20) NOT NULL, created_at VARCHAR(40) NOT NULL, closed_at VARCHAR(40))"))
        db.execute(text("CREATE TABLE IF NOT EXISTS payouts (id VARCHAR(64) PRIMARY KEY, event_id VARCHAR(64) NOT NULL, seller VARCHAR(12) NOT NULL, amount INTEGER NOT NULL, paid_at VARCHAR(40) NOT NULL, actor VARCHAR(100) NOT NULL, note VARCHAR(250) NOT NULL, UNIQUE(event_id,seller))"))
        def column(table,name,definition):
            if e.dialect.name=='postgresql':
                db.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {definition}'))
            else:
                names=[r[1] for r in db.execute(text(f'PRAGMA table_info({table})')).all()]
                if name not in names:db.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))
        column('sellers','commission_bps','INTEGER NOT NULL DEFAULT 2500')
        column('sales','event_id','VARCHAR(64)')
        column('sale_items','commission_bps','INTEGER NOT NULL DEFAULT 2500')
        # Existing sales are deliberately assigned to a clearly named legacy event.
        legacy='legacy-before-v5'
        if not db.execute(text('SELECT 1 FROM flea_events WHERE id=:id'),{'id':legacy}).first():
            db.execute(text('INSERT INTO flea_events (id,name,status,created_at) VALUES (:id,:name,:status,:created)'),dict(id=legacy,name='Tidigare försäljningar (före v5)',status='closed',created=stamp()))
        db.execute(text('UPDATE sales SET event_id=:id WHERE event_id IS NULL'),{'id':legacy})
        # New sales require an explicitly created/open event.

def require_event_open(db,event_id):
    event=db.execute(text('SELECT status FROM flea_events WHERE id=:id'),{'id':event_id}).mappings().first()
    if not event or event['status']!='open':raise HTTPException(409,'Loppisen är avslutad eller saknas. Ändringar är låsta.')

def event_for_sale(db):
    events=db.execute(text("SELECT id FROM flea_events WHERE status='open' ORDER BY created_at" + (' FOR UPDATE' if db.engine.dialect.name=='postgresql' else ''))).all()
    if len(events)!=1:raise HTTPException(409,'Exakt ett aktivt loppistillfälle krävs. Skapa/öppna ett under Administration → Loppistillfällen.')
    return events[0][0]

def commission_for_seller(db,number):
    row=db.execute(text('SELECT commission_bps FROM sellers WHERE number=:n AND active=1'),{'n':number}).first()
    if not row:raise HTTPException(422,f'Säljare {number} saknas eller är inaktiv')
    return row[0]

class EventIn(BaseModel):name:str=Field(min_length=2,max_length=150)
class RateIn(BaseModel):rate:float=Field(ge=0,le=100)
class PayoutIn(BaseModel):actor:str=Field(min_length=2,max_length=100);note:str=Field(default='',max_length=250)

@router.get('/api/v5/events')
def events():
    with engine.connect() as db:
        rows=db.execute(text('SELECT id,name,status,created_at,closed_at FROM flea_events ORDER BY created_at DESC')).mappings().all()
    return {'events':[dict(r) for r in rows]}

@router.post('/api/v5/events',status_code=201)
def create_event(payload:EventIn):
    with engine.begin() as db:
        if db.execute(text("SELECT 1 FROM flea_events WHERE status='open'")).first():raise HTTPException(409,'Avsluta den aktiva loppisen innan du skapar nästa')
        eid=str(uuid.uuid4());db.execute(text('INSERT INTO flea_events (id,name,status,created_at) VALUES (:id,:name,:status,:at)'),dict(id=eid,name=payload.name,status='open',at=stamp()))
    return {'id':eid,'status':'open'}

@router.post('/api/v5/events/{eid}/close')
def close_event(eid:str):
    with engine.begin() as db:
        if db.engine.dialect.name=='postgresql':
            db.execute(text('SELECT id FROM flea_events WHERE id=:id FOR UPDATE'),{'id':eid}).first()
        require_event_open(db,eid)
        # Closing is irreversible via this API. All payouts are recorded later.
        db.execute(text("UPDATE flea_events SET status='closed',closed_at=:at WHERE id=:id"),{'at':stamp(),'id':eid})
    return {'ok':True,'note':'Loppisen är låst. Inga pengar har skickats.'}

@router.put('/api/v5/sellers/{number}/commission')
def set_commission(number:str,payload:RateIn):
    with engine.begin() as db:
        result=db.execute(text('UPDATE sellers SET commission_bps=:rate WHERE number=:n'),{'rate':rate_bps(payload.rate),'n':number})
        if not result.rowcount:raise HTTPException(404,'Säljare saknas')
    return {'number':number,'commission_percent':payload.rate,'note':'Bara framtida varurader påverkas'}

@router.get('/api/v5/sellers/commissions')
def commissions():
    with engine.connect() as db:
        rows=db.execute(text('SELECT number,name,commission_bps FROM sellers ORDER BY number')).mappings().all()
    return {'sellers':[{'number':r['number'],'name':r['name'],'commission_percent':r['commission_bps']/100} for r in rows]}

def settlement_rows(db,eid):
    event=db.execute(text('SELECT id,name,status FROM flea_events WHERE id=:id'),{'id':eid}).mappings().first()
    if not event:raise HTTPException(404,'Loppis saknas')
    items=db.execute(text('''SELECT si.seller,si.id,si.price,si.commission_bps,
       COALESCE((SELECT SUM(a.amount) FROM adjustments a WHERE a.sale_item_id=si.id),0) AS correction
       FROM sale_items si JOIN sales sa ON sa.id=si.sale_id WHERE sa.event_id=:id'''),{'id':eid}).mappings().all()
    grouped={}
    for item in items:
        seller=item['seller']; r=grouped.setdefault(seller,{'seller':seller,'items':0,'gross':0,'commission':0,'due':0})
        amount=item['price']+item['correction'];fee,due=payout_split(amount,item['commission_bps'])
        r['items']+=1;r['gross']+=amount;r['commission']+=fee;r['due']+=due
    paid=db.execute(text('SELECT seller,amount,paid_at,actor FROM payouts WHERE event_id=:id'),{'id':eid}).mappings().all()
    paid_by={r['seller']:dict(r) for r in paid}
    rows=[]
    for seller,r in sorted(grouped.items(),key=lambda p:(len(p[0]),p[0])):
        p=paid_by.get(seller);rows.append({**r,'paid':p['amount'] if p else 0,'paid_at':p['paid_at'] if p else None,'remaining':r['due']-(p['amount'] if p else 0)})
    return dict(event),rows

@router.get('/api/v5/events/{eid}/settlement')
def settlement(eid:str):
    with engine.connect() as db:event,rows=settlement_rows(db,eid)
    return {'event':event,'sellers':rows,'totals':{k:sum(r[k] for r in rows) for k in ('gross','commission','due','paid','remaining')},'note':'Kronavrundning sker per varurad. Historiska v4-köp har standardprovision 25 % tills de granskats. Inga automatiska överföringar.'}

@router.post('/api/v5/events/{eid}/payouts/{seller}',status_code=201)
def mark_paid(eid:str,seller:str,payload:PayoutIn):
    with engine.begin() as db:
        event,rows=settlement_rows(db,eid)
        if event['status']!='closed':raise HTTPException(409,'Avsluta loppisen före utbetalning')
        row=next((r for r in rows if r['seller']==seller),None)
        if not row:raise HTTPException(404,'Ingen försäljning för säljaren')
        if row['paid_at']:raise HTTPException(409,'Utbetalning redan registrerad')
        if row['due']<0:raise HTTPException(409,'Negativt utbetalningsbelopp kräver manuell utredning')
        db.execute(text('INSERT INTO payouts (id,event_id,seller,amount,paid_at,actor,note) VALUES (:id,:event,:seller,:amount,:at,:actor,:note)'),dict(id=str(uuid.uuid4()),event=eid,seller=seller,amount=row['due'],at=stamp(),actor=payload.actor,note=payload.note))
    return {'ok':True,'amount':row['due'],'note':'Endast bokförd markering; ingen betalning har skickats'}

@router.get('/api/v5/events/{eid}/settlement.csv')
def settlement_csv(eid:str):
    data=settlement(eid);out=io.StringIO();out.write('\ufeff');w=csv.writer(out,delimiter=';')
    w.writerow(['Säljnummer','Varor','Försäljning kr','Provision kr','Att betala kr','Markerat utbetalt kr','Kvar kr','Utbetalningsdatum'])
    for r in data['sellers']:w.writerow([r['seller'],r['items'],r['gross'],r['commission'],r['due'],r['paid'],r['remaining'],r['paid_at'] or ''])
    return StreamingResponse(iter([out.getvalue().encode('utf-8')]),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="slutavrakning.csv"'})

@router.get('/events')
def event_page():
    from pathlib import Path
    return FileResponse(Path(__file__).parent/'static'/'events.html')
