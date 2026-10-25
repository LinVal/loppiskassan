"""Loppiskassan v2: demonstrator, NOT production-ready. HTTPS at reverse proxy."""
import os, uuid, secrets, datetime, pathlib, hmac, base64
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from io import BytesIO
import boto3
from botocore.exceptions import ClientError
import qrcode

ROOT=pathlib.Path(__file__).parent
UPLOAD=ROOT/'uploads'; UPLOAD.mkdir(exist_ok=True)
S3_BUCKET=os.getenv('S3_BUCKET')
S3=boto3.client('s3', endpoint_url=os.getenv('S3_ENDPOINT_URL') or None, region_name=os.getenv('AWS_DEFAULT_REGION','eu-north-1')) if S3_BUCKET else None
DATABASE_URL=os.getenv('DATABASE_URL',f'sqlite:///{ROOT / "demo.db"}')
if DATABASE_URL.startswith('postgres://'): DATABASE_URL='postgresql+psycopg://'+DATABASE_URL[len('postgres://'):]
elif DATABASE_URL.startswith('postgresql://'): DATABASE_URL='postgresql+psycopg://'+DATABASE_URL[len('postgresql://'):]
engine=create_engine(DATABASE_URL,connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {},pool_pre_ping=True)
app=FastAPI(title='Loppiskassan – Heroku test')

@app.middleware('http')
async def demo_access(request:Request, call_next):
    # The temporary mobile page and one-time upload link are intentionally token-based.
    path=request.url.path
    if path == '/health' or path == '/mobile' or path.startswith('/api/mobile/'):
        return await call_next(request)
    user=os.getenv('DEMO_USER')
    password=os.getenv('DEMO_PASSWORD')
    if not user or not password:
        return Response('DEMO_USER and DEMO_PASSWORD must be configured', status_code=503)
    auth=request.headers.get('authorization','')
    try:
        scheme, encoded=auth.split(' ',1)
        raw=base64.b64decode(encoded,validate=True).decode('utf-8')
        given_user,given_password=raw.split(':',1)
        valid = (
    scheme.lower() == 'basic'
    and hmac.compare_digest(
        given_user.encode('utf-8'),
        user.encode('utf-8')
    )
    and hmac.compare_digest(
        given_password.encode('utf-8'),
        password.encode('utf-8')
    )
)
    except (ValueError,UnicodeError):
        valid=False
    if not valid:
        return Response('Authentication required',status_code=401,headers={'WWW-Authenticate':'Basic realm="Loppiskassan test"'})
    return await call_next(request)

@app.get('/health')
def health(): return {'ok':True}

with engine.begin() as db:
    db.execute(text('CREATE TABLE IF NOT EXISTS sessions (id VARCHAR(64) PRIMARY KEY, register_no VARCHAR(16) NOT NULL, created_at VARCHAR(40) NOT NULL, status VARCHAR(20) NOT NULL)'))
    db.execute(text('CREATE TABLE IF NOT EXISTS pairings (token VARCHAR(100) PRIMARY KEY, session_id VARCHAR(64) NOT NULL, expires_at VARCHAR(40) NOT NULL, used INTEGER NOT NULL DEFAULT 0)'))
    db.execute(text('CREATE TABLE IF NOT EXISTS photos (id VARCHAR(64) PRIMARY KEY, session_id VARCHAR(64) NOT NULL, filename VARCHAR(150) NOT NULL, created_at VARCHAR(40) NOT NULL)'))
    db.execute(text('CREATE TABLE IF NOT EXISTS sales (id VARCHAR(64) PRIMARY KEY, session_id VARCHAR(64) UNIQUE NOT NULL, register_no VARCHAR(16) NOT NULL, total INTEGER NOT NULL, method VARCHAR(40) NOT NULL, recipient VARCHAR(150) NOT NULL, created_at VARCHAR(40) NOT NULL)'))
    db.execute(text('CREATE TABLE IF NOT EXISTS sale_items (id VARCHAR(64) PRIMARY KEY, sale_id VARCHAR(64) NOT NULL, seller VARCHAR(12) NOT NULL, description VARCHAR(200), price INTEGER NOT NULL)'))

def now(): return datetime.datetime.now(datetime.timezone.utc)
def iso(d): return d.isoformat()
def session_row(db,sid): return db.execute(text('SELECT id,register_no,status FROM sessions WHERE id=:id'),{'id':sid}).mappings().first()

class NewSession(BaseModel):
    register_no: str=Field(min_length=1,max_length=16)
class Item(BaseModel):
    seller: str=Field(pattern=r'^\d{1,4}$')
    desc: str=Field(default='',max_length=200)
    price: int=Field(gt=0,le=1000000)
class Sale(BaseModel):
    items: list[Item]=Field(min_length=1)
    method: str=Field(max_length=40)
    recipient: str=Field(min_length=1,max_length=150)
    payment_confirmed: bool

@app.post('/api/sessions')
def new_session(payload:NewSession):
    sid=str(uuid.uuid4())
    with engine.begin() as db:
        db.execute(text('INSERT INTO sessions VALUES (:id,:r,:c,:s)'),dict(id=sid,r=payload.register_no,c=iso(now()),s='open'))
    return {'session_id':sid,'register_no':payload.register_no}

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
        if not p or p['used'] or datetime.datetime.fromisoformat(p['expires_at'])<now(): raise HTTPException(403,'Länken har gått ut eller använts')
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
        db.execute(text('UPDATE pairings SET used=1 WHERE token=:t'),{'t':token})
    return {'photo_id':pid,'status':'uploaded','note':'Ingen AI-tolkning är ansluten ännu'}

@app.get('/api/sessions/{sid}/photos')
def photos(sid:str):
    with engine.connect() as db:
        if not session_row(db,sid): raise HTTPException(404,'Köp saknas')
        rows=db.execute(text('SELECT id,created_at FROM photos WHERE session_id=:s ORDER BY created_at DESC'),{'s':sid}).mappings().all()
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
    return FileResponse(UPLOAD/row['filename'],headers={'Cache-Control':'no-store'})

@app.post('/api/sessions/{sid}/sale')
def save_sale(sid:str,payload:Sale):
    if not payload.payment_confirmed: raise HTTPException(400,'Betalning måste bekräftas manuellt')
    with engine.begin() as db:
        s=session_row(db,sid)
        if not s: raise HTTPException(404,'Köp saknas')
        existing=db.execute(text('SELECT id,total FROM sales WHERE session_id=:s'),{'s':sid}).mappings().first()
        if existing: return {'sale_id':existing['id'],'total':existing['total'],'already_saved':True}
        if s['status']!='open': raise HTTPException(409,'Köp är stängt')
        sale_id=str(uuid.uuid4()); total=sum(x.price for x in payload.items)
        db.execute(text('INSERT INTO sales VALUES (:id,:s,:r,:t,:m,:p,:c)'),dict(id=sale_id,s=sid,r=s['register_no'],t=total,m=payload.method,p=payload.recipient,c=iso(now())))
        for x in payload.items:
            db.execute(text('INSERT INTO sale_items VALUES (:id,:s,:seller,:d,:p)'),dict(id=str(uuid.uuid4()),s=sale_id,seller=x.seller,d=x.desc,p=x.price))
        db.execute(text("UPDATE sessions SET status='closed' WHERE id=:s"),{'s':sid})
    return {'sale_id':sale_id,'total':total,'already_saved':False}

@app.get('/api/sales')
def sales():
    with engine.connect() as db:
        rows=db.execute(text('SELECT id,register_no,total,method,recipient,created_at FROM sales ORDER BY created_at DESC LIMIT 200')).mappings().all()
    return {'sales':[dict(r) for r in rows]}

@app.get('/api/sellers/summary')
def summary():
    with engine.connect() as db:
        rows=db.execute(text('SELECT seller, COUNT(*) AS items, SUM(price) AS total FROM sale_items GROUP BY seller ORDER BY seller')).mappings().all()
    return {'sellers':[dict(r) for r in rows]}

@app.get('/mobile')
def mobile(): return FileResponse(ROOT/'static'/'mobile.html')
app.mount('/',StaticFiles(directory=ROOT/'static',html=True),name='frontend')
