import hashlib
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from jose import JWTError, jwt
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import DateTime, String, Text, create_engine, func, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./socialintel.db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
ALGORITHM = "HS256"

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

app = FastAPI(title="Unified Social Intelligence Platform", version="1.0.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])

class Login(BaseModel):
    email: str
    password: str

class RecordIn(BaseModel):
    source: str = Field(min_length=2, max_length=32)
    external_id: str = Field(min_length=1, max_length=512)
    author: str | None = Field(default=None, max_length=512)
    text: str | None = Field(default=None, max_length=100000)
    url: HttpUrl | None = None
    published_at: datetime | None = None

class CrawlRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=25)

class FacebookRequest(BaseModel):
    page_id: str = Field(min_length=1, max_length=128)
    limit: int = Field(default=25, ge=1, le=100)

def token_for(email: str) -> str:
    return jwt.encode({"sub": email, "exp": datetime.now(timezone.utc) + timedelta(hours=12)}, JWT_SECRET, algorithm=ALGORITHM)

def current_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=[ALGORITHM])
        return str(payload["sub"])
    except (JWTError, KeyError):
        raise HTTPException(401, "Invalid or expired token")

def save_record(data: dict) -> int:
    source = str(data["source"])
    external_id = str(data["external_id"])
    text = data.get("text") or ""
    fingerprint = hashlib.sha256(f"{source}|{external_id}|{text}".encode()).hexdigest()
    with SessionLocal() as db:
        existing = db.scalar(select(Record).where(Record.source == source, Record.external_id == external_id))
        if existing:
            return existing.id
        row = Record(source=source, external_id=external_id, author=data.get("author"), text=text, url=data.get("url"), published_at=data.get("published_at"), fingerprint=fingerprint)
        db.add(row); db.commit(); db.refresh(row)
        return row.id

@app.get("/health")
def health(): return {"status": "ok", "service": "social-intelligence"}

@app.post("/auth/login")
def login(body: Login):
    if body.email != ADMIN_EMAIL or body.password != ADMIN_PASSWORD:
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": token_for(body.email), "token_type": "bearer"}

@app.get("/records")
def records(q: str | None = Query(default=None, max_length=500), source: str | None = Query(default=None, max_length=32), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), _: str = Depends(current_user)):
    with SessionLocal() as db:
        stmt = select(Record)
        count_stmt = select(func.count()).select_from(Record)
        conditions = []
        if source: conditions.append(Record.source == source)
        if q:
            pattern = f"%{q}%"; conditions.append(or_(Record.text.ilike(pattern), Record.author.ilike(pattern)))
        if conditions:
            stmt = stmt.where(*conditions); count_stmt = count_stmt.where(*conditions)
        total = db.scalar(count_stmt) or 0
        rows = db.scalars(stmt.order_by(Record.created_at.desc()).offset(offset).limit(limit)).all()
        return {"total": total, "items": [{"id": r.id, "source": r.source, "external_id": r.external_id, "author": r.author, "text": r.text, "url": r.url, "published_at": r.published_at, "created_at": r.created_at} for r in rows]}

@app.post("/records")
def ingest(body: RecordIn, _: str = Depends(current_user)):
    return {"id": save_record(body.model_dump()), "status": "stored"}

@app.post("/crawl")
async def crawl(body: CrawlRequest, _: str = Depends(current_user)):
    imported = 0
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "SocialIntel/1.0 public-data-client"}) as client:
        for url in body.urls:
            parsed = urlparse(str(url))
            if parsed.scheme not in {"http", "https"}: continue
            response = await client.get(str(url)); response.raise_for_status()
            if "text/html" not in response.headers.get("content-type", ""): continue
            text = response.text[:100000]
            title = text.split("<title>", 1)[1].split("</title>", 1)[0][:500] if "<title>" in text and "</title>" in text else ""
            rid = save_record({"source": "web", "external_id": hashlib.sha256(str(url).encode()).hexdigest(), "author": title, "text": text, "url": str(url)})
            imported += 1 if rid else 0
    return {"imported": imported}

@app.post("/facebook/feed")
async def facebook(body: FacebookRequest, _: str = Depends(current_user)):
    token = os.getenv("META_ACCESS_TOKEN")
    version = os.getenv("META_GRAPH_VERSION", "v23.0")
    if not token: raise HTTPException(503, "META_ACCESS_TOKEN is not configured")
    endpoint = f"https://graph.facebook.com/{version}/{body.page_id}/feed"
    params = {"access_token": token, "limit": body.limit, "fields": "id,message,created_time,permalink_url,from"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(endpoint, params=params); response.raise_for_status(); payload = response.json()
    imported = 0
    for item in payload.get("data", []):
        save_record({"source":"facebook", "external_id":item.get("id"), "author":(item.get("from") or {}).get("name"), "text":item.get("message"), "url":item.get("permalink_url"), "published_at":item.get("created_time")})
        imported += 1
    return {"imported": imported}

@app.get("/webhooks/whatsapp")
def whatsapp_verify(request: Request):
    mode = request.query_params.get("hub.mode"); verify_token = request.query_params.get("hub.verify_token"); challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and verify_token == os.getenv("WHATSAPP_VERIFY_TOKEN"): return int(challenge or "0")
    raise HTTPException(403, "Verification failed")

@app.post("/webhooks/whatsapp")
def whatsapp_webhook(payload: dict):
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                save_record({"source":"whatsapp", "external_id":message.get("id"), "author":message.get("from"), "text":message.get("text",{}).get("body"), "metadata":message})
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD)

DASHBOARD = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Social Intel</title><style>body{font-family:system-ui;margin:0;background:#0b1020;color:#eef}main{max-width:1100px;margin:auto;padding:24px}input,button{padding:11px;border-radius:8px;border:1px solid #334;background:#111a2c;color:#fff}button{background:#315efb;cursor:pointer}.bar{display:flex;gap:10px}.bar input{flex:1}.card{background:#121a2d;border:1px solid #26324e;padding:16px;margin:12px 0;border-radius:12px}.tag{font-size:12px;opacity:.7;text-transform:uppercase}</style></head><body><main><h1>Social Intelligence</h1><div class="bar"><input id="email" value="admin@example.com"><input id="password" type="password" placeholder="Password"><button onclick="login()">Login</button></div><br><div class="bar"><input id="q" placeholder="Search records"><button onclick="search()">Search</button></div><section id="results"></section></main><script>let token=localStorage.token;async function login(){let r=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:email.value,password:password.value})});let d=await r.json();if(!r.ok)return alert(d.detail||'Login failed');token=d.access_token;localStorage.token=token;search()}async function search(){if(!token)return;let r=await fetch('/records?q='+encodeURIComponent(q.value),{headers:{Authorization:'Bearer '+token}});let d=await r.json();if(!r.ok)return alert(d.detail||'Unauthorized');results.innerHTML=d.items.map(x=>`<article class="card"><div class="tag">${x.source}</div><h3>${escapeHtml(x.author||'Unknown')}</h3><p>${escapeHtml(x.text||'')}</p>${x.url?`<a href="${x.url}" target="_blank">Open</a>`:''}</article>`).join('')}function escapeHtml(s){return s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}if(token)search()</script></body></html>'''
