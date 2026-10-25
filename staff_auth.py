# Per-staff HTTP Basic accounts. For development; use TLS and rotate bootstrap credentials.
import base64, datetime, hashlib, hmac, os, secrets, uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from pathlib import Path

router=APIRouter()
engine=None

def hash_password(password, salt=None):
    salt=salt or os.urandom(16)
    return salt.hex()+'$'+hashlib.scrypt(password.encode('utf-8'),salt=salt,n=2**14,r=8,p=1).hex()

def verify(password, stored):
    try:
        salt, digest=stored.split('$',1)
        check=hash_password(password,bytes.fromhex(salt)).split('$',1)[1]
        return hmac.compare_digest(check,digest)
    except (ValueError,TypeError): return False

def install_staff(db_engine):
    global engine;engine=db_engine
    with engine.begin() as db:
        if engine.dialect.name=='postgresql': db.execute(text('SELECT pg_advisory_xact_lock(87420016)'))
        db.execute(text('''CREATE TABLE IF NOT EXISTS staff_users (
          id VARCHAR(64) PRIMARY KEY, username VARCHAR(100) NOT NULL UNIQUE,
          password_hash VARCHAR(256) NOT NULL, role VARCHAR(16) NOT NULL,
          active INTEGER NOT NULL DEFAULT 1, created_at VARCHAR(40) NOT NULL)'''))
        db.execute(text('''CREATE TABLE IF NOT EXISTS staff_audit (
          id VARCHAR(64) PRIMARY KEY, actor VARCHAR(100) NOT NULL,
          method VARCHAR(10) NOT NULL, path VARCHAR(300) NOT NULL,
          status INTEGER NOT NULL, created_at VARCHAR(40) NOT NULL)'''))
        if not db.execute(text('SELECT 1 FROM staff_users LIMIT 1')).first():
            username=os.getenv('DEMO_USER'); password=os.getenv('DEMO_PASSWORD')
            if not username or not password:
                raise RuntimeError('Vid första start krävs DEMO_USER och DEMO_PASSWORD för administratören')
            db.execute(text('INSERT INTO staff_users VALUES (:id,:u,:p,:role,1,:at)'),
                dict(id=str(uuid.uuid4()),u=username,p=hash_password(password),role='admin',at=datetime.datetime.now(datetime.timezone.utc).isoformat()))

def required_role(path,method):
    if path=='/health' or path=='/mobile' or path=='/seller' or path.startswith('/api/portal/') or path.startswith('/api/mobile/'):
        return None
    if path=='/api/staff/change-password': return 'cashier'
    if path.startswith('/api/staff') or path=='/staff': return 'admin'
    if path.startswith('/api/v5/events') and method in ('POST','PUT','PATCH','DELETE'):return 'admin'
    if path.startswith('/api/v5/events/') and ('settlement' in path or 'payouts' in path):return 'admin'
    if path.startswith('/api/v5/sellers/') and method in ('PUT','POST','PATCH','DELETE'):return 'admin'
    if path.startswith('/api/v4/sellers') and method in ('POST','PUT','PATCH','DELETE'):return 'admin'
    if path.startswith('/api/v4/adjustments') and method=='POST':return 'admin'
    if path in ('/admin','/events'):return 'admin'
    if path.startswith('/api/v4/reports') or path.startswith('/api/v5/events/') and ('settlement' in path or 'payouts' in path):return 'admin'
    return 'cashier'

async def staff_middleware(request:Request,call_next):
    path=request.url.path; method=request.method
    role=required_role(path,method)
    if role is None:return await call_next(request)
    auth=request.headers.get('authorization','')
    username=None;password=None
    try:
        scheme, encoded=auth.split(' ',1)
        if scheme.lower()=='basic':
            username,password=base64.b64decode(encoded,validate=True).decode('utf-8').split(':',1)
    except (ValueError,UnicodeError):pass
    user=None
    if username is not None:
        with engine.connect() as db:
            user=db.execute(text('SELECT username,password_hash,role FROM staff_users WHERE username=:u AND active=1'),{'u':username}).mappings().first()
    if not user or not verify(password,user['password_hash']):
        return Response('Inloggning krävs',status_code=401,headers={'WWW-Authenticate':'Basic realm="Loppiskassan personal"'})
    if role=='admin' and user['role']!='admin':return Response('Behörighet saknas',status_code=403)
    request.state.staff_username=user['username']
    request.state.staff_role=user['role']
    response=await call_next(request)
    if method in ('POST','PUT','PATCH','DELETE') and response.status_code<400:
        with engine.begin() as db:
            db.execute(text('INSERT INTO staff_audit VALUES (:id,:actor,:method,:path,:status,:at)'),dict(
                id=str(uuid.uuid4()),actor=user['username'],method=method,path=path[:300],status=response.status_code,
                at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return response

class StaffIn(BaseModel):
    username:str=Field(min_length=2,max_length=100,pattern=r'^[a-zA-Z0-9_.-]+$')
    password:str=Field(min_length=12,max_length=256)
    role:str=Field(pattern='^(admin|cashier)$')

@router.get('/api/staff')
def list_staff():
    with engine.connect() as db:
        rows=db.execute(text('SELECT id,username,role,active,created_at FROM staff_users ORDER BY username')).mappings().all()
    return {'staff':[dict(x) for x in rows]}

@router.post('/api/staff',status_code=201)
def create_staff(payload:StaffIn):
    with engine.begin() as db:
        if db.execute(text('SELECT 1 FROM staff_users WHERE username=:u'),{'u':payload.username}).first():raise HTTPException(409,'Användarnamnet finns redan')
        uid=str(uuid.uuid4())
        db.execute(text('INSERT INTO staff_users VALUES (:id,:u,:p,:role,1,:at)'),dict(id=uid,u=payload.username,p=hash_password(payload.password),role=payload.role,at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    return {'id':uid,'username':payload.username,'role':payload.role}

@router.post('/api/staff/{username}/disable')
def disable_staff(username:str,request:Request):
    if username==request.state.staff_username:raise HTTPException(409,'Du kan inte spärra ditt eget konto')
    with engine.begin() as db:
        result=db.execute(text('UPDATE staff_users SET active=0 WHERE username=:u'),{'u':username})
        if not result.rowcount:raise HTTPException(404,'Kontot finns inte')
    return {'ok':True}

@router.get('/api/staff/audit')
def audit():
    with engine.connect() as db:
        rows=db.execute(text('SELECT actor,method,path,status,created_at FROM staff_audit ORDER BY created_at DESC LIMIT 200')).mappings().all()
    return {'events':[dict(x) for x in rows]}

@router.get('/staff')
def staff_page():return FileResponse(Path(__file__).parent/'static'/'staff.html')

class PasswordChange(BaseModel):
    current_password:str
    new_password:str=Field(min_length=12,max_length=256)

@router.post('/api/staff/change-password')
def change_password(payload:PasswordChange,request:Request):
    username=request.state.staff_username
    with engine.begin() as db:
        row=db.execute(text('SELECT password_hash FROM staff_users WHERE username=:u'),{'u':username}).first()
        if not row or not verify(payload.current_password,row[0]):raise HTTPException(403,'Nuvarande lösenord är fel')
        db.execute(text('UPDATE staff_users SET password_hash=:p WHERE username=:u'),{'p':hash_password(payload.new_password),'u':username})
    return {'ok':True}
