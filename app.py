import hashlib
import hmac
import ipaddress
import os
import socket
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from jose import JWTError, jwt
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import DateTime, String, Text, create_engine, func, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./socialintel.db")
JWT_SECRET = os.getenv("JWT_SECRET", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ALGORITHM = "HS256"
MAX_CRAWL_BYTES = int(os.getenv("MAX_CRAWL_BYTES", "2000000"))

if len(JWT_SECRET) < 32: raise RuntimeError("JWT_SECRET must be at least 32 characters")
if not ADMIN_EMAIL or not ADMIN_PASSWORD: raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD are required")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass
class Record(Base):
    __tablename__ = "records"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    external_id: Mapped[str] = mapped_column(String(512))
    author: Mapped[str | None] = mapped_column(String(512))
    text: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2048))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)
app = FastAPI(title="Unified Social Intelligence Platform", version="1.2.1")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])

class Login(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)
class RecordIn(BaseModel):
    source: str = Field(min_length=2, max_length=32)
    external_id: str = Field(min_length=1, max_length=512)
    author: str | None = Field(default=None, max_length=512)
    text: str | None = Field(default=None, max_length=100000)
    url: HttpUrl | None = None
    published_at: datetime | None = None
class CrawlRequest(BaseModel): urls: list[HttpUrl] = Field(min_length=1, max_length=25)
class FacebookRequest(BaseModel):
    page_id: str = Field(min_length=1, max_length=128)
    limit: int = Field(default=25, ge=1, le=100)
class TelegramRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=50, ge=1, le=100)

def token_for(email: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": email, "iat": now, "exp": now + timedelta(hours=12)}, JWT_SECRET, algorithm=ALGORITHM)

def current_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=[ALGORITHM]); subject = payload.get("sub")
        if not subject: raise ValueError("missing subject")
        return str(subject)
    except (JWTError, ValueError): raise HTTPException(401, "Invalid or expired token")

def parse_datetime(value):
    if not value: return None
    if isinstance(value, datetime): return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError: return None

def save_record(data: dict) -> int:
    source, external_id = str(data["source"]), str(data["external_id"])
    text = data.get("text") or ""
    fingerprint = hashlib.sha256(f"{source}|{external_id}|{text}".encode()).hexdigest()
    with SessionLocal() as db:
        existing = db.scalar(select(Record).where(Record.source == source, Record.external_id == external_id))
        if existing: return existing.id
        row = Record(source=source, external_id=external_id, author=data.get("author"), text=text[:100000], url=str(data["url"]) if data.get("url") else None, published_at=parse_datetime(data.get("published_at")), fingerprint=fingerprint)
        db.add(row); db.commit(); db.refresh(row); return row.id

def assert_public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname: raise HTTPException(400, "Only HTTP(S) URLs are allowed")
    try: infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror: raise HTTPException(400, "Unable to resolve target host")
    for address in {item[4][0] for item in infos}:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified: raise HTTPException(400, "Private or non-public network targets are not allowed")

@app.get("/health")
def health(): return {"status":"ok","service":"social-intelligence","version":"1.2.1"}
@app.post("/auth/login")
def login(body: Login):
    if not hmac.compare_digest(body.email, ADMIN_EMAIL) or not hmac.compare_digest(body.password, ADMIN_PASSWORD): raise HTTPException(401,"Invalid credentials")
    return {"access_token":token_for(body.email),"token_type":"bearer"}
@app.get("/records")
def records(q: str | None = Query(default=None,max_length=500), source: str | None = Query(default=None,max_length=32), limit: int = Query(default=50,ge=1,le=200), offset: int = Query(default=0,ge=0), _: str = Depends(current_user)):
    with SessionLocal() as db:
        stmt, count_stmt = select(Record), select(func.count()).select_from(Record); conditions=[]
        if source: conditions.append(Record.source==source)
        if q:
            pattern=f"%{q}%"; conditions.append(or_(Record.text.ilike(pattern),Record.author.ilike(pattern)))
        if conditions: stmt=stmt.where(*conditions); count_stmt=count_stmt.where(*conditions)
        total=db.scalar(count_stmt) or 0; rows=db.scalars(stmt.order_by(Record.created_at.desc()).offset(offset).limit(limit)).all()
        return {"total":total,"items":[{"id":r.id,"source":r.source,"external_id":r.external_id,"author":r.author,"text":r.text,"url":r.url,"published_at":r.published_at,"created_at":r.created_at} for r in rows]}
@app.post("/records")
def ingest(body: RecordIn, _: str = Depends(current_user)): return {"id":save_record(body.model_dump()),"status":"stored"}
@app.post("/crawl")
async def crawl(body: CrawlRequest, _: str = Depends(current_user)):
    imported=0
    async with httpx.AsyncClient(timeout=20,follow_redirects=False,headers={"User-Agent":"SocialIntel/1.2 public-data-client"}) as client:
        for url in body.urls:
            target=str(url); assert_public_host(target)
            try:
                async with client.stream("GET", target) as response:
                    if response.status_code >= 400 or "text/html" not in response.headers.get("content-type", ""): continue
                    chunks=[]; total=0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > MAX_CRAWL_BYTES: raise HTTPException(413, "Response exceeds crawl size limit")
                        chunks.append(chunk)
                    text=b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")[:100000]
                external=hashlib.sha256(f"{target}|{text[:4000]}".encode()).hexdigest(); save_record({"source":"web","external_id":external,"text":text,"url":target}); imported+=1
            except HTTPException: raise
            except (httpx.HTTPError, UnicodeError): continue
    return {"imported":imported}
@app.post("/telegram/search")
async def telegram_search(body: TelegramRequest, _: str = Depends(current_user)):
    api_id, api_hash, session = os.getenv("TELEGRAM_API_ID"), os.getenv("TELEGRAM_API_HASH"), os.getenv("TELEGRAM_SESSION")
    if not all((api_id,api_hash,session)): raise HTTPException(503,"Telegram credentials/session are not configured")
    try:
        from hydrogram import Client
        client=Client("socialintel",api_id=int(api_id),api_hash=api_hash,session_string=session); count=0; await client.start()
        try:
            async for message in client.search_global(body.query,limit=body.limit):
                text=message.text or message.caption or ""; chat_id=getattr(getattr(message,"chat",None),"id","unknown")
                save_record({"source":"telegram","external_id":f"{chat_id}:{message.id}","author":getattr(getattr(message,"from_user",None),"username",None),"text":text}); count+=1
        finally: await client.stop()
        return {"imported":count}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(502,f"Telegram connector error: {type(exc).__name__}")
@app.post("/facebook/feed")
async def facebook(body: FacebookRequest, _: str = Depends(current_user)):
    token=os.getenv("META_ACCESS_TOKEN")
    if not token: raise HTTPException(503,"META_ACCESS_TOKEN is not configured")
    endpoint=f"https://graph.facebook.com/{os.getenv('META_GRAPH_VERSION','v23.0')}/{body.page_id}/feed"; params={"access_token":token,"limit":body.limit,"fields":"id,message,created_time,permalink_url,from"}
    async with httpx.AsyncClient(timeout=30) as client:
        response=await client.get(endpoint,params=params)
        if response.status_code>=400: raise HTTPException(response.status_code,"Meta API request failed")
        payload=response.json()
    for item in payload.get("data",[]):
        if item.get("id"): save_record({"source":"facebook","external_id":item["id"],"author":(item.get("from") or {}).get("name"),"text":item.get("message"),"url":item.get("permalink_url"),"published_at":item.get("created_time")})
    return {"imported":len(payload.get("data",[]))}
@app.get("/webhooks/whatsapp")
def whatsapp_verify(request: Request):
    expected=os.getenv("WHATSAPP_VERIFY_TOKEN","")
    if request.query_params.get("hub.mode")=="subscribe" and expected and hmac.compare_digest(request.query_params.get("hub.verify_token", ""), expected): return int(request.query_params.get("hub.challenge") or "0")
    raise HTTPException(403,"Verification failed")
@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    secret=os.getenv("WHATSAPP_APP_SECRET","")
    if not secret: raise HTTPException(503,"WHATSAPP_APP_SECRET is not configured")
    raw=await request.body(); signature=request.headers.get("X-Hub-Signature-256",""); expected="sha256="+hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature): raise HTTPException(401,"Invalid webhook signature")
    payload=await request.json(); count=0
    for entry in payload.get("entry",[]):
        for change in entry.get("changes",[]):
            for message in change.get("value",{}).get("messages",[]):
                if message.get("id"): save_record({"source":"whatsapp","external_id":message["id"],"author":message.get("from"),"text":message.get("text",{}).get("body")}); count+=1
    return {"ok":True,"imported":count}
@app.get("/",response_class=HTMLResponse)
def dashboard(): return HTMLResponse(DASHBOARD)
DASHBOARD='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Social Intel</title><style>body{font-family:system-ui;margin:0;background:#0b1020;color:#eef}main{max-width:1100px;margin:auto;padding:24px}input,button{padding:11px;border-radius:8px;border:1px solid #334;background:#111a2c;color:#fff}button{background:#315efb;cursor:pointer}.bar{display:flex;gap:10px}.bar input{flex:1}.card{background:#121a2d;border:1px solid #26324e;padding:16px;margin:12px 0;border-radius:12px}.tag{font-size:12px;opacity:.7;text-transform:uppercase}</style></head><body><main><h1>Social Intelligence</h1><div class="bar"><input id="email"><input id="password" type="password" placeholder="Password"><button onclick="login()">Login</button></div><br><div class="bar"><input id="q" placeholder="Search records"><button onclick="search()">Search</button></div><section id="results"></section></main><script>let token=localStorage.token;async function login(){let r=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:email.value,password:password.value})});let d=await r.json();if(!r.ok)return alert(d.detail||'Login failed');token=d.access_token;localStorage.token=token;search()}async function search(){if(!token)return;let r=await fetch('/records?q='+encodeURIComponent(q.value),{headers:{Authorization:'Bearer '+token}});let d=await r.json();if(!r.ok)return alert(d.detail||'Unauthorized');results.innerHTML=d.items.map(x=>`<article class="card"><div class="tag">${escapeHtml(x.source)}</div><h3>${escapeHtml(x.author||'Unknown')}</h3><p>${escapeHtml(x.text||'')}</p>${x.url?`<a href="${x.url}" target="_blank" rel="noopener">Open</a>`:''}</article>`).join('')}function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}if(token)search()</script></body></html>'''
