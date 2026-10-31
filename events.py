"""Event-specific settlement, commission snapshots and manual payout ledger (v5)."""
import csv, io, uuid, datetime, re
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
        db.execute(text("CREATE TABLE IF NOT EXISTS event_sellers (event_id VARCHAR(64) NOT NULL, number VARCHAR(12) NOT NULL, name VARCHAR(150) NOT NULL, seller_type VARCHAR(20) NOT NULL DEFAULT 'external', assigned_at VARCHAR(40) NOT NULL, PRIMARY KEY(event_id,number))"))
        db.execute(text("CREATE TABLE IF NOT EXISTS seller_identities (id VARCHAR(64) PRIMARY KEY, name VARCHAR(150) NOT NULL, created_at VARCHAR(40) NOT NULL)"))
        db.execute(text("CREATE TABLE IF NOT EXISTS event_seller_audit (id VARCHAR(64) PRIMARY KEY, event_id VARCHAR(64) NOT NULL, number VARCHAR(12) NOT NULL, old_name VARCHAR(150), new_name VARCHAR(150), actor VARCHAR(100) NOT NULL, created_at VARCHAR(40) NOT NULL)"))
        db.execute(text("CREATE TABLE IF NOT EXISTS payouts (id VARCHAR(64) PRIMARY KEY, event_id VARCHAR(64) NOT NULL, seller VARCHAR(12) NOT NULL, amount INTEGER NOT NULL, paid_at VARCHAR(40) NOT NULL, actor VARCHAR(100) NOT NULL, note VARCHAR(250) NOT NULL, UNIQUE(event_id,seller))"))
        def column(table,name,definition):
            if e.dialect.name=='postgresql':
                db.execute(text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {definition}'))
            else:
                names=[r[1] for r in db.execute(text(f'PRAGMA table_info({table})')).all()]
                if name not in names:db.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))
        column('event_sellers','identity_id','VARCHAR(64)')
        # Migrate existing assignments without merging people based on names.
        missing=db.execute(text('SELECT event_id,number,name FROM event_sellers WHERE identity_id IS NULL')).all()
        for eid,number,name in missing:
            sid=str(uuid.uuid4())
            db.execute(text('INSERT INTO seller_identities (id,name,created_at) VALUES (:id,:name,:at)'),{'id':sid,'name':name,'at':stamp()})
            db.execute(text('UPDATE event_sellers SET identity_id=:sid WHERE event_id=:e AND number=:n'),{'sid':sid,'e':eid,'n':number})
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

def validate_event_seller(db,event_id,number):
    row=db.execute(text('SELECT name FROM event_sellers WHERE event_id=:e AND number=:n'),{'e':event_id,'n':str(int(number))}).first()
    if not row:raise HTTPException(422,f'Säljnummer {number} är inte tilldelat i den aktiva loppisen')
    return row[0]

def commission_for_seller(db,number):
    row=db.execute(text('SELECT commission_bps FROM sellers WHERE number=:n AND active=1'),{'n':number}).first()
    if not row:raise HTTPException(422,f'Säljare {number} saknas eller är inaktiv')
    return row[0]

class EventIn(BaseModel):name:str=Field(min_length=2,max_length=150)
class AssignmentIn(BaseModel):
    number:int=Field(ge=1,le=250)
    name:str=Field(min_length=1,max_length=150)
    seller_type:str=Field(default='external',pattern='^(staff|external)$')
    actor:str=Field(default='Administratör',min_length=2,max_length=100)
    identity_id:str|None=None

class CsvIn(BaseModel):
    content:str=Field(min_length=1,max_length=150000)
    actor:str=Field(default='Administratör',min_length=2,max_length=100)

class CopyIn(BaseModel):
    source_event_id:str=Field(min_length=1,max_length=64)
    seller_type:str=Field(default='staff',pattern='^(staff|external|all)$')
    actor:str=Field(default='Administratör',min_length=2,max_length=100)

def parse_seller_csv(content):
    content=content.lstrip('\ufeff')
    try:
        dialect=csv.Sniffer().sniff(content[:4096],delimiters=';,\t')
        reader=csv.DictReader(io.StringIO(content),dialect=dialect)
        if not reader.fieldnames:raise ValueError('Rubrikrad saknas')
        headers={str(h).strip().lower():h for h in reader.fieldnames if h}
        number_col=next((headers[k] for k in ('nummer','säljnummer','saljnummer','number') if k in headers),None)
        name_col=next((headers[k] for k in ('namn','name') if k in headers),None)
        type_col=next((headers[k] for k in ('typ','type','säljartyp','saljartyp') if k in headers),None)
        identity_col=next((headers[k] for k in ('person_id','identity_id','säljar_id','saljar_id') if k in headers),None)
        if not number_col or not name_col:raise ValueError('Rubrikerna nummer och namn krävs')
        rows=[];seen=set()
        for line,row in enumerate(reader,start=2):
            if None in row:raise ValueError(f'Rad {line}: för många kolumner')
            raw=(row.get(number_col) or '').strip();name=(row.get(name_col) or '').strip()
            if not raw and not name:continue
            if not re.fullmatch(r'[0-9]{1,3}',raw) or not 1<=int(raw)<=250:raise ValueError(f'Rad {line}: nummer måste vara 1–250')
            number=str(int(raw))
            if number in seen:raise ValueError(f'Rad {line}: nummer {number} förekommer flera gånger')
            seen.add(number)
            if not name or len(name)>150:raise ValueError(f'Rad {line}: namn saknas eller är för långt')
            typ=(row.get(type_col) or 'external').strip().lower() if type_col else 'external'
            typ={'medarbetare':'staff','extern':'external'}.get(typ,typ)
            if typ not in ('staff','external'):raise ValueError(f'Rad {line}: typ ska vara medarbetare eller extern')
            identity=(row.get(identity_col) or '').strip() if identity_col else ''
            rows.append((number,name,typ,identity or None))
            if len(rows)>250:raise ValueError('Högst 250 säljare')
        if not rows:raise ValueError('Inga säljare hittades')
        return rows
    except csv.Error as exc:raise ValueError('CSV-filen kan inte läsas') from exc

def resolve_identity(db,name,identity_id=None):
    """Never infer identity from name: two people can share a name."""
    if identity_id:
        row=db.execute(text('SELECT id FROM seller_identities WHERE id=:id'),{'id':identity_id}).first()
        if not row:raise HTTPException(422,'Okänt permanent säljar-ID')
        return row[0]
    sid=str(uuid.uuid4())
    db.execute(text('INSERT INTO seller_identities (id,name,created_at) VALUES (:id,:name,:at)'),{'id':sid,'name':name,'at':stamp()})
    return sid

@router.get('/api/v5/seller-identities')
def list_seller_identities(q:str='',limit:int=100):
    # Identity is never inferred from name; search is for a human to choose.
    if len(q)>150 or not 1<=limit<=250:raise HTTPException(422,'Ogiltig sökning')
    with engine.connect() as db:
        rows=db.execute(text('SELECT id,name,created_at FROM seller_identities WHERE LOWER(name) LIKE :q ORDER BY name,id LIMIT :limit'),{'q':'%'+q.strip().lower()+'%','limit':limit}).mappings().all()
    return {'sellers':[dict(row) for row in rows]}

@router.get('/api/v5/seller-identities/{identity_id}/history')
def seller_identity_history(identity_id:str):
    with engine.connect() as db:
        identity=db.execute(text('SELECT id,name,created_at FROM seller_identities WHERE id=:id'),{'id':identity_id}).mappings().first()
        if not identity:raise HTTPException(404,'Säljaridentiteten saknas')
        rows=db.execute(text('SELECT es.event_id,fe.name AS event_name,fe.status AS event_status,es.number,es.name AS assigned_name,es.seller_type FROM event_sellers es JOIN flea_events fe ON fe.id=es.event_id WHERE es.identity_id=:id ORDER BY fe.created_at DESC,es.number'),{'id':identity_id}).mappings().all()
    return {'seller':dict(identity),'events':[dict(r) for r in rows]}

def apply_assignments(db,eid,rows,actor):
    event=db.execute(text('SELECT status FROM flea_events WHERE id=:e'+(' FOR UPDATE' if db.engine.dialect.name=='postgresql' else '')),{'e':eid}).first()
    if not event:raise HTTPException(404,'Loppis saknas')
    if event[0]!='draft':raise HTTPException(409,'Massimport och kopiering kan bara göras i utkast')
    existing={r[0] for r in db.execute(text('SELECT number FROM event_sellers WHERE event_id=:e'),{'e':eid}).all()}
    rows=[tuple(r) if len(r)==4 else (*r,None) for r in rows]
    conflicts=[n for n,_,_,_ in rows if n in existing]
    if conflicts:raise HTTPException(409,'Numren är redan tilldelade: '+', '.join(conflicts[:20])+'. Frigör dem innan import.')
    for number,name,typ,identity_id in rows:
        identity_id=resolve_identity(db,name,identity_id)
        db.execute(text('INSERT INTO event_sellers (event_id,number,name,seller_type,assigned_at,identity_id) VALUES (:e,:n,:name,:type,:at,:sid)'),{'e':eid,'n':number,'name':name,'type':typ,'at':stamp(),'sid':identity_id})
        db.execute(text('INSERT INTO event_seller_audit (id,event_id,number,old_name,new_name,actor,created_at) VALUES (:id,:e,:n,NULL,:new,:actor,:at)'),{'id':str(uuid.uuid4()),'e':eid,'n':number,'new':name,'actor':actor,'at':stamp()})
        # Sale processing also uses the global seller table for commission rates.
        # Do not overwrite existing seller identities or their commission settings.
        old=db.execute(text('SELECT active FROM sellers WHERE number=:n'),{'n':number}).first()
        if old is None:
            db.execute(text('INSERT INTO sellers (number,name,active,created_at) VALUES (:n,:name,1,:at)'),{'n':number,'name':name,'at':stamp()})
        elif not old[0]:
            raise HTTPException(409,f'Säljnummer {number} är inaktivt i grundregistret. Aktivera det först.')
    return len(rows)

@router.post('/api/v5/events/{eid}/sellers/import')
def import_sellers(eid:str,payload:CsvIn):
    try:rows=parse_seller_csv(payload.content)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    with engine.begin() as db:count=apply_assignments(db,eid,rows,payload.actor)
    return {'imported':count,'status':'ok'}

@router.post('/api/v5/events/{eid}/sellers/copy')
def copy_sellers(eid:str,payload:CopyIn):
    if eid==payload.source_event_id:raise HTTPException(422,'Välj ett annat evenemang som källa')
    with engine.begin() as db:
        source=db.execute(text('SELECT 1 FROM flea_events WHERE id=:id'),{'id':payload.source_event_id}).first()
        if not source:raise HTTPException(404,'Källevenemanget saknas')
        rows=db.execute(text('SELECT number,name,seller_type,identity_id FROM event_sellers WHERE event_id=:e'),{'e':payload.source_event_id}).all()
        selected=[(n,name,typ,sid) for n,name,typ,sid in rows if payload.seller_type=='all' or typ==payload.seller_type]
        if not selected:raise HTTPException(422,'Inga säljare av vald typ att kopiera')
        count=apply_assignments(db,eid,selected,payload.actor)
    return {'copied':count,'status':'ok'}

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
        eid=str(uuid.uuid4());db.execute(text('INSERT INTO flea_events (id,name,status,created_at) VALUES (:id,:name,:status,:at)'),dict(id=eid,name=payload.name,status='draft',at=stamp()))
    return {'id':eid,'status':'draft'}

@router.get('/api/v5/events/{eid}/sellers')
def event_sellers(eid:str):
    with engine.connect() as db:
        event=db.execute(text('SELECT status FROM flea_events WHERE id=:id'),{'id':eid}).first()
        if not event:raise HTTPException(404,'Loppis saknas')
        rows=db.execute(text('SELECT number,name,seller_type,identity_id FROM event_sellers WHERE event_id=:e ORDER BY LENGTH(number),number'),{'e':eid}).mappings().all()
    return {'status':event[0],'assigned':[dict(x) for x in rows],'available':250-len(rows)}

def readiness_summary(status, assigned):
    """One shared readiness policy for the admin UI and event start."""
    issues=[]
    if not assigned: issues.append('Tilldela minst en namngiven säljare.')
    missing=[str(r['number']) for r in assigned if not str(r['name'] or '').strip()]
    if missing: issues.append('Namn saknas för nummer: '+', '.join(missing))
    invalid=[str(r['number']) for r in assigned if not str(r['number']).isdigit() or not 1<=int(r['number'])<=250]
    if invalid: issues.append('Ogiltiga nummer: '+', '.join(invalid))
    identities=[r['identity_id'] for r in assigned if r['identity_id']]
    if len(identities)!=len(set(identities)):
        issues.append('En person har tilldelats flera nummer i samma evenemang.')
    return {'status':status,'ready':status=='draft' and not issues,'issues':issues,
            'assigned':len(assigned),'staff':sum(r['seller_type']=='staff' for r in assigned),
            'external':sum(r['seller_type']=='external' for r in assigned),
            'available':250-len(assigned)}

@router.get('/api/v5/events/{eid}/readiness')
def event_readiness(eid:str):
    with engine.connect() as db:
        event=db.execute(text('SELECT status FROM flea_events WHERE id=:e'),{'e':eid}).first()
        if not event:raise HTTPException(404,'Loppis saknas')
        rows=db.execute(text('SELECT number,name,seller_type,identity_id FROM event_sellers WHERE event_id=:e'),{'e':eid}).mappings().all()
    return readiness_summary(event[0],rows)

@router.put('/api/v5/events/{eid}/sellers')
def assign_event_seller(eid:str,payload:AssignmentIn):
    name=payload.name.strip()
    if not name:raise HTTPException(422,'Säljaren måste ha ett namn')
    number=str(payload.number)
    with engine.begin() as db:
        event=db.execute(text('SELECT status FROM flea_events WHERE id=:e'),{'e':eid}).first()
        if not event:raise HTTPException(404,'Loppis saknas')
        if event[0]=='closed':raise HTTPException(409,'Avslutad loppis kan inte ändras')
        previous=db.execute(text('SELECT name,identity_id FROM event_sellers WHERE event_id=:e AND number=:n'),{'e':eid,'n':number}).first()
        # A number that has been sold under must never be reassigned.
        used=db.execute(text('SELECT 1 FROM sale_items si JOIN sales sa ON sa.id=si.sale_id WHERE sa.event_id=:e AND si.seller=:n LIMIT 1'),{'e':eid,'n':number}).first()
        if used and previous and (previous[0]!=name or (payload.identity_id and payload.identity_id!=previous[1])):raise HTTPException(409,'Numret har försäljning och får inte byta ägare')
        if payload.identity_id:
            duplicate=db.execute(text('SELECT number FROM event_sellers WHERE event_id=:e AND identity_id=:sid AND number<>:n'),{'e':eid,'sid':payload.identity_id,'n':number}).first()
            if duplicate:raise HTTPException(409,f'Personen är redan tilldelad nummer {duplicate[0]} i detta evenemang')
        if previous:
            sid=resolve_identity(db,name,payload.identity_id) if payload.identity_id else previous[1]
            db.execute(text('UPDATE event_sellers SET name=:name,seller_type=:type,identity_id=:sid WHERE event_id=:e AND number=:n'),{'name':name,'type':payload.seller_type,'sid':sid,'e':eid,'n':number})
        else:
            sid=resolve_identity(db,name,payload.identity_id)
            db.execute(text('INSERT INTO event_sellers (event_id,number,name,seller_type,assigned_at,identity_id) VALUES (:e,:n,:name,:type,:at,:sid)'),{'e':eid,'n':number,'name':name,'type':payload.seller_type,'at':stamp(),'sid':sid})
        db.execute(text('INSERT INTO event_seller_audit (id,event_id,number,old_name,new_name,actor,created_at) VALUES (:id,:e,:n,:old,:new,:actor,:at)'),{'id':str(uuid.uuid4()),'e':eid,'n':number,'old':previous[0] if previous else None,'new':name,'actor':payload.actor,'at':stamp()})
    return {'number':number,'name':name,'status':'assigned'}

@router.delete('/api/v5/events/{eid}/sellers/{number}')
def unassign_event_seller(eid:str,number:int,actor:str='Administratör'):
    if not 1<=number<=250:raise HTTPException(422,'Ogiltigt säljnummer')
    with engine.begin() as db:
        event=db.execute(text('SELECT status FROM flea_events WHERE id=:e'),{'e':eid}).first()
        if not event:raise HTTPException(404,'Loppis saknas')
        if event[0]!='draft':raise HTTPException(409,'Nummer kan bara frigöras före start')
        old=db.execute(text('SELECT name FROM event_sellers WHERE event_id=:e AND number=:n'),{'e':eid,'n':str(number)}).first()
        if old:
            db.execute(text('DELETE FROM event_sellers WHERE event_id=:e AND number=:n'),{'e':eid,'n':str(number)})
            db.execute(text('INSERT INTO event_seller_audit (id,event_id,number,old_name,new_name,actor,created_at) VALUES (:id,:e,:n,:old,NULL,:actor,:at)'),{'id':str(uuid.uuid4()),'e':eid,'n':str(number),'old':old[0],'actor':actor,'at':stamp()})
    return {'ok':True}

@router.post('/api/v5/events/{eid}/start')
def start_event(eid:str):
    with engine.begin() as db:
        event=db.execute(text('SELECT status FROM flea_events WHERE id=:e'+(' FOR UPDATE' if db.engine.dialect.name=='postgresql' else '')),{'e':eid}).first()
        if not event:raise HTTPException(404,'Loppis saknas')
        if event[0]!='draft':raise HTTPException(409,'Bara utkast kan startas')
        if db.execute(text("SELECT 1 FROM flea_events WHERE status='open'")).first():raise HTTPException(409,'En annan loppis pågår')
        rows=db.execute(text('SELECT number,name FROM event_sellers WHERE event_id=:e'),{'e':eid}).all()
        summary=readiness_summary('draft',[dict(number=n,name=name,seller_type=typ,identity_id=sid) for n,name,typ,sid in db.execute(text('SELECT number,name,seller_type,identity_id FROM event_sellers WHERE event_id=:e'),{'e':eid}).all()])
        if not summary['ready']:raise HTTPException(409,' '.join(summary['issues']))
        db.execute(text("UPDATE flea_events SET status='open' WHERE id=:e"),{'e':eid})
    return {'id':eid,'status':'open','assigned':len(rows)}

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
