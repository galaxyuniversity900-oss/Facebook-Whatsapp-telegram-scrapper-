# Unified Social Intelligence Platform

A production-oriented unified acquisition and search service for authorized/public social data. It normalizes Telegram, WhatsApp, Facebook and public-web records into one searchable store.

## Features
- FastAPI backend with OpenAPI docs.
- JWT-protected management and search APIs.
- Telegram MTProto search using an authenticated session.
- WhatsApp Cloud API webhook ingestion with mandatory HMAC verification.
- Facebook Graph API feed ingestion using an authorized Meta access token.
- Public-web crawler with HTTP(S)-only validation, private-network blocking, no redirects and response-size limits.
- PostgreSQL-compatible SQLAlchemy persistence; SQLite is convenient for local development.
- Record deduplication and paginated search.
- Minimal responsive browser dashboard.
- Docker and GitHub Actions CI.

## Authorized-use boundary
Use only accounts, pages, chats, groups, channels, websites and APIs for which you have authorization or which are publicly accessible and lawful to collect. This project does not provide credential theft, OTP interception, private-account bypass, CAPTCHA bypass, anti-bot evasion, or unauthorized access.

## Quick start
```bash
cp .env.example .env
# Set JWT_SECRET to a random value of 32+ characters.
# Set ADMIN_EMAIL and ADMIN_PASSWORD.
docker compose up --build
```

Open `/` for the dashboard and `/docs` for interactive API documentation.

## API
- `POST /auth/login` — obtain a JWT.
- `GET /records` — authenticated search with `q`, `source`, `limit`, and `offset`.
- `POST /records` — authenticated normalized-record ingestion.
- `POST /crawl` — authenticated public-web acquisition.
- `POST /telegram/search` — authenticated Telegram search for the configured session.
- `POST /facebook/feed` — authenticated Facebook Graph feed acquisition.
- `GET /webhooks/whatsapp` — Meta webhook verification.
- `POST /webhooks/whatsapp` — verified WhatsApp webhook ingestion.
- `GET /health` — service health endpoint.

## Environment
See `.env.example`. Never commit `.env`, Telegram session files, access tokens, application secrets, or production credentials.

## Tests
```bash
pytest -q
python -m py_compile app.py telegram_connector.py
```

## Production deployment
Set a strong JWT secret and administrator password, restrict `CORS_ORIGINS`, use HTTPS behind a reverse proxy, use managed PostgreSQL, configure platform-approved API permissions, rotate secrets, enable backups and monitoring, and define data-retention/deletion procedures appropriate to your jurisdiction and platform terms.