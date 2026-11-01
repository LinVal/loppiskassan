"""Loppiskassan cashier API."""
import os, uuid, secrets, datetime, pathlib, hmac, base64, json, logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, text
from io import BytesIO
from PIL import Image, ImageOps
import httpx
import boto3
from botocore.exceptions import ClientError
import qrcode

ROOT=pathlib.Path(__file__).parent
UPLOAD=ROOT/'uploads'; UPLOAD.mkdir(exist_ok=True)
# Bucketeer supplies these automatically. Explicit S3_* variables still work.
S3_BUCKET=os.getenv('S3_BUCKET') or os.getenv('BUCKETEER_BUCKET_NAME')
S3_KEY=os.getenv('AWS_ACCESS_KEY_ID') or os.getenv('BUCKETEER_AWS_ACCESS_KEY_ID')
S3_SECRET=os.getenv('AWS_SECRET_ACCESS_KEY') or os.getenv('BUCKETEER_AWS_SECRET_ACCESS_KEY')
S3_REGION=os.getenv('AWS_DEFAULT_REGION') or os.getenv('BUCKETEER_AWS_REGION') or 'us-east-1'
S3=boto3.client('s3', endpoint_url=os.getenv('S3_ENDPOINT_URL') or None,
    region_name=S3_REGION, aws_access_key_id=S3_KEY, aws_secret_access_key=S3_SECRET) if S3_BUCKET else None
DATABASE_URL=os.getenv('DATABASE_URL',f'sqlite:///{ROOT / "demo.db"}')
if DATABASE_URL.startswith('postgres://'): DATABASE_URL='postgresql+psycopg://'+DATABASE_URL[len('postgres://'):]
elif DATABASE_URL.startswith('postgresql://'): DATABASE_URL='postgresql+psycopg://'+DATABASE_URL[len('postgresql://'):]
engine=create_engine(DATABASE_URL,connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {},pool_pre_ping=True)
app=FastAPI(title='Loppiskassan – Heroku test')

from staff_auth import install_staff, staff_middleware
install_staff(engine)
app.middleware('http')(staff_middleware)

@app.get('/health')
def health(): return {'ok':True}

with engine.begin() as db:
    if engine.dialect.name=='postgresql': db.execute(text('SELECT pg_advisory_xact_lock(87420013)'))
    db.execute(text('CREATE TABLE IF NOT EXISTS sessions (id VARCHAR(64) PRIMARY KEY, register_no VARCHAR(16) NOT NULL, created_at VARCHAR(40) NOT NULL, status VARCHAR(20) NOT NULL)'))
    db.execute(text('CREATE TABLE IF NOT EXISTS pairings (token VARCHAR(100) PRIMARY KEY, session_id VARCHAR(64) NOT NULL, expires_at VARCHAR(40) NOT NULL, used INTEGER NOT NULL DEFAULT 0)'))
    db.execute(text('CREATE TABLE IF NOT EXISTS photos (id VARCHAR(64) PRIMARY KEY, session_id VARCHAR(64) NOT NULL, filename VARCHAR(150) NOT NULL, created_at VARCHAR(40) NOT NULL)'))
    db.execute(text('CREATE TABLE IF NOT EXISTS qr_scans (id VARCHAR(64) PRIMARY KEY, session_id VARCHAR(64) NOT NULL, seller VARCHAR(4) NOT NULL, price INTEGER NOT NULL, description VARCHAR(200) NOT NULL, created_at VARCHAR(40) NOT NULL)'))
    db.execute(text('CREATE TABLE IF NOT EXISTS sales (id VARCHAR(64) PRIMARY KEY, session_id VARCHAR(64) UNIQUE NOT NULL, register_no VARCHAR(16) NOT NULL, total INTEGER NOT NULL, method VARCHAR(40) NOT NULL, recipient VARCHAR(150) NOT NULL, created_at VARCHAR(40) NOT NULL)'))
    db.execute(text('CREATE TABLE IF NOT EXISTS sale_items (id VARCHAR(64) PRIMARY KEY, sale_id VARCHAR(64) NOT NULL, seller VARCHAR(12) NOT NULL, description VARCHAR(200), price INTEGER NOT NULL)'))
    db.execute(text('''CREATE TABLE IF NOT EXISTS item_evidence (item_id VARCHAR(64) PRIMARY KEY, photo_id VARCHAR(64), ai_seller VARCHAR(12), ai_price INTEGER, ai_description VARCHAR(200), ai_uncertain INTEGER NOT NULL DEFAULT 1, FOREIGN KEY(item_id) REFERENCES sale_items(id))'''))
    db.execute(text('''CREATE TABLE IF NOT EXISTS register_reconciliations (id VARCHAR(64) PRIMARY KEY, event_id VARCHAR(64) NOT NULL, register_no VARCHAR(16) NOT NULL, method VARCHAR(40) NOT NULL, counted_amount INTEGER NOT NULL, expected_amount INTEGER NOT NULL, actor VARCHAR(100) NOT NULL, note VARCHAR(500), created_at VARCHAR(40) NOT NULL)'''))

def now(): return datetime.datetime.now(datetime.timezone.utc)
def iso(d): return d.isoformat()
def session_row(db,sid): return db.execute(text('SELECT id,register_no,status FROM sessions WHERE id=:id'),{'id':sid}).mappings().first()

class NewSession(BaseModel):
    register_no: str=Field(min_length=1,max_length=16)
class Item(BaseModel):
    seller: str=Field(pattern=r'^\d{1,4}$')
    desc: str=Field(default='',max_length=200)
    price: int=Field(gt=0,le=1000000, strict=True)
    photo_id: str | None = None
    ai_seller: str | None = Field(default=None,max_length=12)
    ai_price: int | None = None
    ai_description: str | None = Field(default=None,max_length=200)
    ai_uncertain: bool = True

    @field_validator('price')
    @classmethod
    def multiple_of_five(cls, value: int) -> int:
        if value % 5 != 0:
            raise ValueError('Priset måste vara delbart med 5 kr')
        return value

class Sale(BaseModel):
    items: list[Item]=Field(min_length=1)
    method: str=Field(max_length=40)
    recipient: str=Field(min_length=1,max_length=150)
    payment_confirmed: bool
    cash_received: int | None = Field(default=None, ge=0, strict=True)

    @field_validator("method")
    @classmethod
    def valid_method(cls, value: str) -> str:
        if value not in ("Swish", "Kontant", "Kort"):
            raise ValueError("Välj Swish, Kontant eller Kort")
        return value

@app.post('/api/sessions')
def new_session(payload:NewSession):
    sid=str(uuid.uuid4())
    with engine.begin() as db:
        db.execute(text('INSERT INTO sessions VALUES (:id,:r,:c,:s)'),dict(id=sid,r=payload.register_no,c=iso(now()),s='open'))
    return {'session_id':sid,'register_no':payload.register_no}

@app.get('/api/sessions/{sid}/status')
def sale_session_status(sid: str):
    with engine.connect() as db:
        row = session_row(db, sid)
        if not row:
            raise HTTPException(404, 'Köp saknas')
        sale = db.execute(text('SELECT id,total FROM sales WHERE session_id=:s'), {'s':sid}).mappings().first()
    return {'status': 'closed' if sale else row['status'],
            'sale_id': sale['id'] if sale else None,
            'total': sale['total'] if sale else None}


@app.post('/api/sessions/{sid}/pair')
def pair(sid:str,request:Request):
    token=secrets.token_urlsafe(24)
    expires=now()+datetime.timedelta(minutes=5)
    with engine.begin() as db:
        row=session_row(db,sid)
        if not row or row['status']!='open': raise HTTPException(404,'Köp saknas eller är stängt')
        db.execute(text('INSERT INTO pairings VALUES (:t,:s,:e,0)'),dict(t=token,s=sid,e=iso(expires)))
    base=os.getenv('PUBLIC_BASE_URL','').rstrip('/') or str(request.base_url).rstrip('/')
    return {'url':f'{base}/mobile?token={token}','expires_at':iso(expires)}

@app.get('/api/pair/qr')
def pair_qr(url:str,request:Request):
    # Prevent QR endpoint being used for arbitrary external URLs.
    if not url.startswith((os.getenv('PUBLIC_BASE_URL','').rstrip('/') or str(request.base_url).rstrip('/'))+'/mobile?token=') or len(url)>500: raise HTTPException(400,'Ogiltig länk')
    img=qrcode.make(url); output=BytesIO();img.save(output,format='PNG')
    return Response(output.getvalue(),media_type='image/png')

@app.post('/api/mobile/{token}/photo')
async def mobile_photo(token:str,photo:UploadFile=File(...)):
    with engine.begin() as db:
        p=db.execute(text('SELECT * FROM pairings WHERE token=:t'),{'t':token}).mappings().first()
        if not p or datetime.datetime.fromisoformat(p['expires_at'])<now(): raise HTTPException(403,'Länken har gått ut eller använts')
        s=session_row(db,p['session_id'])
        if not s or s['status']!='open': raise HTTPException(409,'Köpet är stängt')
        content=await photo.read(12_000_001)
        if len(content)>12_000_000: raise HTTPException(413,'Max 12 MB')
        if not (content.startswith(b'\xff\xd8\xff') or content.startswith(b'\x89PNG\r\n\x1a\n') or content[4:12] in (b'ftypheic',b'ftypheix',b'ftypmif1')): raise HTTPException(415,'Använd JPEG, PNG eller HEIC')
        ext='.jpg' if content.startswith(b'\xff\xd8') else '.png' if content.startswith(b'\x89PNG') else '.heic'
        pid=str(uuid.uuid4()); filename=pid+ext
        if S3:
            S3.put_object(Bucket=S3_BUCKET,Key='photos/'+filename,Body=content,ContentType='image/jpeg' if ext=='.jpg' else 'image/png' if ext=='.png' else 'image/heic',ServerSideEncryption='AES256')
        else:
            (UPLOAD/filename).write_bytes(content)
        db.execute(text('INSERT INTO photos VALUES (:id,:s,:f,:c)'),dict(id=pid,s=p['session_id'],f=filename,c=iso(now())))
    return {'photo_id':pid,'status':'uploaded','note':'Bilden är sparad. AI-avläsning görs i kassan.'}

class QRScan(BaseModel):
    scan_id: str = Field(min_length=36,max_length=36)
    payload: str = Field(min_length=7,max_length=260)

@app.post('/api/mobile/{token}/qr')
def mobile_qr(token: str, data: QRScan):
    """QR is only a proposal; cashier must review it before payment."""
    try:
        uuid.UUID(data.scan_id)
    except ValueError:
        raise HTTPException(422,'Ogiltigt skannings-ID')
    parts=data.payload.split('|',3)
    if len(parts)!=4 or parts[0]!='LK1' or not parts[1].isdigit() or not parts[2].isdigit():
        raise HTTPException(422,'Okänd QR-kod. Använd Loppiskassans testlappar (LK1).')
    seller,price,desc=parts[1],int(parts[2]),parts[3]
    if not (1<=int(seller)<=250 and 5<=price<=1000000 and price%5==0 and len(desc)<=200):
        raise HTTPException(422,'Ogiltigt säljnummer eller pris. Priset ska vara delbart med 5.')
    with engine.begin() as db:
        pairing=db.execute(text('SELECT * FROM pairings WHERE token=:t'),{'t':token}).mappings().first()
        if not pairing or datetime.datetime.fromisoformat(pairing['expires_at'])<now():
            raise HTTPException(403,'Mobilkopplingen har gått ut. Koppla om mobilen.')
        session=session_row(db,pairing['session_id'])
        if not session or session['status']!='open': raise HTTPException(409,'Köpet är stängt')
        existing=db.execute(text('SELECT id FROM qr_scans WHERE id=:id'),{'id':data.scan_id}).first()
        if existing: return {'status':'already_received','scan_id':data.scan_id}
        db.execute(text('INSERT INTO qr_scans VALUES (:id,:sid,:seller,:price,:description,:created)'),
          {'id':data.scan_id,'sid':pairing['session_id'],'seller':str(int(seller)),'price':price,'description':desc,'created':iso(now())})
    return {'status':'received','scan_id':data.scan_id}

@app.post('/api/mobile/{token}/qr-photo')
async def mobile_qr_photo(token: str, photo: UploadFile = File(...)):
    """Decode a photographed QR code on the server (Safari-compatible)."""
    import cv2
    import numpy as np
    content = await photo.read(6_000_001)
    if len(content) > 6_000_000:
        raise HTTPException(413, 'QR-bilden får vara högst 6 MB')
    if not (content.startswith(b'\xff\xd8\xff') or content.startswith(b'\x89PNG\r\n\x1a\n')):
        raise HTTPException(415, 'Använd JPEG eller PNG för QR-foto')
    picture = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if picture is None or picture.shape[0] * picture.shape[1] > 20_000_000:
        raise HTTPException(422, 'Bilden kunde inte läsas')
    payload, _, _ = cv2.QRCodeDetector().detectAndDecode(picture)
    if not payload:
        raise HTTPException(422, 'Ingen QR-kod hittades. Håll kameran stilla och fyll bilden med koden.')
    # Camera sends repeated frames; suppress the same code for a short window.
    parts = payload.split('|', 3)
    if len(parts) == 4 and parts[0] == 'LK1':
        with engine.connect() as db:
            pairing = db.execute(text('SELECT * FROM pairings WHERE token=:t'), {'t': token}).mappings().first()
            if pairing and datetime.datetime.fromisoformat(pairing['expires_at']) >= now():
                previous = db.execute(text('SELECT created_at FROM qr_scans WHERE session_id=:sid AND seller=:seller AND price=:price AND description=:description ORDER BY created_at DESC LIMIT 1'),
                    {'sid': pairing['session_id'], 'seller': str(int(parts[1])) if parts[1].isdigit() else parts[1], 'price': int(parts[2]) if parts[2].isdigit() else -1, 'description': parts[3]}).first()
                if previous and (now() - datetime.datetime.fromisoformat(previous[0])).total_seconds() < 4.5:
                    return {'status': 'already_received', 'payload': payload}
    result = mobile_qr(token, QRScan(scan_id=str(uuid.uuid4()), payload=payload))
    return {**result, 'payload': payload}

@app.get('/api/sessions/{sid}/qr-scans')
def session_qr_scans(sid: str):
    with engine.connect() as db:
        if not session_row(db,sid): raise HTTPException(404,'Köp saknas')
        rows=db.execute(text('SELECT id,seller,price,description FROM qr_scans WHERE session_id=:sid ORDER BY created_at,id'),{'sid':sid}).mappings().all()
    return {'scans':[dict(r) for r in rows]}

@app.get('/api/sessions/{sid}/photos')
def photos(sid:str):
    with engine.connect() as db:
        if not session_row(db,sid): raise HTTPException(404,'Köp saknas')
        rows=db.execute(text('SELECT id,created_at FROM photos WHERE session_id=:s ORDER BY created_at ASC'),{'s':sid}).mappings().all()
    return {'photos':[dict(r, url=f'/api/sessions/{sid}/photos/{r["id"]}') for r in rows]}

@app.get('/api/sessions/{sid}/photos/{pid}')
def get_photo(sid:str,pid:str):
    with engine.connect() as db:
        row=db.execute(text('SELECT filename FROM photos WHERE id=:id AND session_id=:s'),dict(id=pid,s=sid)).mappings().first()
    if not row: raise HTTPException(404,'Bild saknas')
    if S3:
        try:
            obj=S3.get_object(Bucket=S3_BUCKET,Key='photos/'+row['filename'])
        except ClientError:
            raise HTTPException(404,'Bild saknas')
        return StreamingResponse(obj['Body'].iter_chunks(),media_type=obj.get('ContentType','application/octet-stream'),headers={'Cache-Control':'no-store'})
    if not (UPLOAD/row['filename']).exists(): raise HTTPException(404,'Bilden har försvunnit från den tillfälliga disken')
    return FileResponse(UPLOAD/row['filename'],headers={'Cache-Control':'no-store'})

def photo_bytes(sid: str, pid: str) -> bytes:
    with engine.connect() as db:
        row=db.execute(text('SELECT filename FROM photos WHERE id=:id AND session_id=:s'), {'id':pid,'s':sid}).mappings().first()
    if not row: raise HTTPException(404,'Bild saknas')
    if S3:
        try:
            return S3.get_object(Bucket=S3_BUCKET, Key='photos/'+row['filename'])['Body'].read(12_000_001)
        except ClientError:
            raise HTTPException(404,'Bilden finns inte i Bucketeer')
    path=UPLOAD/row['filename']
    if not path.exists(): raise HTTPException(404,'Bilden har försvunnit vid omstart; aktivera Bucketeer')
    return path.read_bytes()

@app.post('/api/sessions/{sid}/photos/{pid}/analyze')
async def analyze_photo(sid: str, pid: str):
    """AI suggestions only. Never saves a sale or marks an item as verified."""
    key=os.getenv('OPENAI_API_KEY')
    if not key: raise HTTPException(503,'Sätt OPENAI_API_KEY i Heroku Config Vars för AI-avläsning')
    with engine.connect() as db:
        session=session_row(db,sid)
    if not session or session['status']!='open': raise HTTPException(409,'Starta ett aktivt serverköp')
    raw=photo_bytes(sid,pid)
    if len(raw)>12_000_000: raise HTTPException(413,'Bilden är för stor')
    try:
        im=Image.open(BytesIO(raw))
        im=ImageOps.exif_transpose(im).convert('RGB')
        im.thumbnail((2200,2200))
        out=BytesIO(); im.save(out,format='JPEG',quality=86)
        encoded=base64.b64encode(out.getvalue()).decode('ascii')
    except Exception:
        raise HTTPException(415,'AI-avläsning stöder JPEG och PNG. Konvertera HEIC till JPEG.')
    instructions=('Du granskar ett A4-ark med handskrivna prislappar från en svensk loppis. '
      'Identifiera VARJE separat fysisk prislapp, inklusive små och överlappande lappar. '
      'För varje lapp: inringat säljnummer (1-4 siffror), pris i hela kronor, eventuell storlek/märke. '
      'Gissa ALDRIG oläsliga siffror: använd tom sträng för säljare och 0 för okänt pris. '
      'Ange uncertain=true vid minsta tvekan. Returnera endast JSON-objekt med nycklarna '
      'items (array) och note (kort svensk kommentar). Varje item: '
      'seller (string), price (integer), desc (string), uncertain (boolean), '
      'x,y,w,h (nummer i procent 0-100, ungefärlig rektangel kring lappen). '
      'En rad per fysisk lapp, läs i ordning uppifrån och ned. '
      'Alla förslag måste kontrolleras mot originalbilden innan köp registreras.')
    payload={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),
      'temperature':0,'response_format':{'type':'json_object'},
      'messages':[{'role':'system','content':instructions},
        {'role':'user','content':[{'type':'text','text':'Läs alla lappar. Returnera JSON.'},
          {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+encoded,'detail':'high'}}]}],
      'max_tokens':4000}
    try:
        async with httpx.AsyncClient(timeout=110) as client:
            resp=await client.post('https://api.openai.com/v1/chat/completions',
                headers={'Authorization':'Bearer '+key},json=payload)
        if resp.status_code!=200:
            logging.warning('AI API returned status %s',resp.status_code)
            raise HTTPException(502,'AI-tjänsten kunde inte läsa bilden (HTTP '+str(resp.status_code)+'). Kontrollera API-nyckel och saldo.')
        result=json.loads(resp.json()['choices'][0]['message']['content'])
    except HTTPException: raise
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        logging.warning('AI analysis failed: %s',type(exc).__name__)
        raise HTTPException(502,'AI-avläsningen misslyckades. Försök igen eller mata in manuellt.')
    if not isinstance(result,dict) or not isinstance(result.get('items'),list):
        raise HTTPException(502,'AI gav ett oväntat resultat')
    cleaned=[]
    for i,r in enumerate(result['items'][:100],1):
        if not isinstance(r,dict): continue
        seller=str(r.get('seller') or '').strip()
        if not seller.isascii() or not seller.isdigit() or len(seller)>4: seller=''
        try: price=int(r.get('price') or 0)
        except (ValueError,TypeError): price=0
        if not 0<price<=1_000_000: price=0
        def coord(k,default):
            try:return max(0,min(100,float(r.get(k,default))))
            except (TypeError,ValueError):return default
        cleaned.append({'id':i,'seller':seller,'price':price,'desc':str(r.get('desc') or '')[:200],
          'uncertain':bool(r.get('uncertain',True)) or not seller or not price or price % 5 != 0,
          'x':coord('x',0),'y':coord('y',0),'w':coord('w',0),'h':coord('h',0)})
    return {'items':cleaned,'count':len(cleaned),'note':str(result.get('note') or '')[:500],
       'warning':'AI kan missa lappar eller läsa fel. Kontrollera ALLA lappar mot fotot innan försäljning.'}

@app.post('/api/sessions/{sid}/sale')
def save_sale(sid:str,payload:Sale):
    if not payload.payment_confirmed: raise HTTPException(400,'Betalning måste bekräftas manuellt')
    if payload.method == 'Kontant' and (payload.cash_received is None or payload.cash_received < sum(x.price for x in payload.items)):
        raise HTTPException(400, 'Mottaget kontantbelopp måste täcka totalsumman')
    with engine.begin() as db:
        if engine.dialect.name=='postgresql':
            db.execute(text('SELECT id FROM sessions WHERE id=:id FOR UPDATE'),{'id':sid}).first()
        s=session_row(db,sid)
        if not s: raise HTTPException(404,'Köp saknas')
        existing=db.execute(text('SELECT id,total FROM sales WHERE session_id=:s'),{'s':sid}).mappings().first()
        if existing: return {'sale_id':existing['id'],'total':existing['total'],'already_saved':True}
        if s['status']!='open': raise HTTPException(409,'Köp är stängt')
        sale_id=str(uuid.uuid4()); total=sum(x.price for x in payload.items)
        from events import event_for_sale, commission_for_seller, validate_event_seller
        event_id=event_for_sale(db)
        db.execute(text('INSERT INTO sales (id,session_id,register_no,total,method,recipient,created_at,event_id) VALUES (:id,:s,:r,:t,:m,:p,:c,:e)'),dict(id=sale_id,s=sid,r=s['register_no'],t=total,m=payload.method,p=payload.recipient,c=iso(now()),e=event_id))
        for x in payload.items:
            if x.photo_id and not db.execute(text('SELECT 1 FROM photos WHERE id=:p AND session_id=:s'),{'p':x.photo_id,'s':sid}).first():
                raise HTTPException(422,'Originalbilden tillhör inte köpet')
            validate_event_seller(db,event_id,x.seller)
            rate=commission_for_seller(db,x.seller)
            item_id=str(uuid.uuid4())
            db.execute(text('INSERT INTO sale_items (id,sale_id,seller,description,price,commission_bps) VALUES (:id,:s,:seller,:d,:p,:bps)'),dict(id=item_id,s=sale_id,seller=x.seller,d=x.desc,p=x.price,bps=rate))
            if x.photo_id:
                db.execute(text('INSERT INTO item_evidence VALUES (:id,:photo,:seller,:price,:description,:uncertain)'),dict(id=item_id,photo=x.photo_id,seller=x.ai_seller,price=x.ai_price,description=x.ai_description,uncertain=int(x.ai_uncertain)))
        db.execute(text("UPDATE sessions SET status='closed' WHERE id=:s"),{'s':sid})
    return {'sale_id':sale_id,'total':total,'already_saved':False}

@app.get('/api/sales')
def sales():
    with engine.connect() as db:
        rows=db.execute(text('SELECT id,register_no,total,method,recipient,created_at FROM sales ORDER BY created_at DESC LIMIT 200')).mappings().all()
    return {'sales':[dict(r) for r in rows]}

@app.get('/api/cashier/recent-sales')
def cashier_recent_sales(request:Request, register_no:str, limit:int=10):
    # Only sales from requested register
    if not register_no or len(register_no)>16: raise HTTPException(422,'Ogiltigt kassanummer')
    with engine.connect() as db:
        rows=db.execute(text('SELECT id,total,method,created_at FROM sales WHERE register_no=:r ORDER BY created_at DESC LIMIT :n'),{'r':register_no,'n':max(1,min(limit,25))}).mappings().all()
    return {'sales':[dict(x) for x in rows]}

class Reconciliation(BaseModel):
    event_id:str
    register_no:str=Field(min_length=1,max_length=16)
    method:str=Field(pattern='^(Swish|Kontant|Kort)$')
    counted_amount:int=Field(ge=0,strict=True)
    note:str=Field(default='',max_length=500)

@app.get('/api/admin/register-reconciliation')
def register_reconciliation(event_id:str):
    with engine.connect() as db:
        rows=db.execute(text('''SELECT register_no,method,COUNT(*) AS sales_count,SUM(total) AS expected_amount FROM sales WHERE event_id=:e GROUP BY register_no,method ORDER BY register_no,method'''),{'e':event_id}).mappings().all()
        checks=db.execute(text('''SELECT register_no,method,counted_amount,expected_amount,actor,note,created_at FROM register_reconciliations WHERE event_id=:e ORDER BY created_at DESC'''),{'e':event_id}).mappings().all()
    return {'expected':[dict(r) for r in rows],'reconciliations':[dict(r,difference=r['counted_amount']-r['expected_amount']) for r in checks], 'note':'Avstämning av manuellt rapporterade belopp. Ingen automatisk kontroll mot Swish- eller kortleverantör.'}

@app.post('/api/admin/register-reconciliation',status_code=201)
def save_reconciliation(payload:Reconciliation,request:Request):
    with engine.begin() as db:
        if not db.execute(text('SELECT 1 FROM events WHERE id=:e'),{'e':payload.event_id}).first():raise HTTPException(404,'Loppistillfället saknas')
        expected=db.execute(text('SELECT COALESCE(SUM(total),0) FROM sales WHERE event_id=:e AND register_no=:r AND method=:m'),{'e':payload.event_id,'r':payload.register_no,'m':payload.method}).scalar_one()
        db.execute(text('INSERT INTO register_reconciliations VALUES (:id,:e,:r,:m,:counted,:expected,:actor,:note,:at)'),dict(id=str(uuid.uuid4()),e=payload.event_id,r=payload.register_no,m=payload.method,counted=payload.counted_amount,expected=expected,actor=request.state.staff_username,note=payload.note,at=iso(now())))
    return {'expected_amount':expected,'counted_amount':payload.counted_amount,'difference':payload.counted_amount-expected}

@app.get('/api/sellers/summary')
def summary():
    with engine.connect() as db:
        rows=db.execute(text('SELECT seller, COUNT(*) AS items, SUM(price) AS total FROM sale_items GROUP BY seller ORDER BY seller')).mappings().all()
    return {'sellers':[dict(r) for r in rows]}

@app.get('/mobile')
def mobile(): return FileResponse(ROOT/'static'/'mobile.html')
from sellers import router as v4_router, install as install_v4
install_v4(engine)
app.include_router(v4_router)
from staff_auth import router as staff_router
app.include_router(staff_router)
from events import router as v5_router, install as install_v5
install_v5(engine)
app.include_router(v5_router)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static-assets')
app.mount('/',StaticFiles(directory=ROOT/'static',html=True),name='frontend')
