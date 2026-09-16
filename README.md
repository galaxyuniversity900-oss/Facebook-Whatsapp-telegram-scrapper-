# Unified Social Intelligence Platform

Production-oriented unified acquisition and search platform for authorized/public social data.

## Connectors
- Telegram: MTProto session for chats the authenticated account is authorized to access.
- WhatsApp: Meta Cloud API webhook ingestion for an owned business account.
- Facebook: Meta Graph API for resources permitted by the token.
- Public Web: HTTP acquisition of public pages.

## Architecture
FastAPI API + PostgreSQL + Redis/RQ + React/Vite-style static dashboard. Records are normalized into one schema, deduplicated by source/external ID, indexed in PostgreSQL, and exposed through authenticated APIs.

## Security
Secrets are environment variables. JWT authentication protects management/search endpoints. CORS is configurable. The project intentionally does not implement credential theft, OTP interception, private-account bypass, CAPTCHA bypass, anti-bot evasion, or unauthorized collection.

## Run
```bash
cp .env.example .env
docker compose up --build
```
API: http://localhost:8000  
Docs: http://localhost:8000/docs  
Dashboard: http://localhost:8000/

## Production checklist
Use strong secrets, TLS/reverse proxy, managed PostgreSQL/Redis, restrictive CORS, secret rotation, backups, monitoring, retention policies, and platform-approved API permissions before deployment.