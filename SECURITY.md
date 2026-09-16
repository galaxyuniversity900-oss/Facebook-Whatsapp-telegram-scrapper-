# Security Policy

The default branch is the supported development line.

## Authorized use
Use this project only for public data or resources that the operator is authorized to access. Do not bypass authentication, CAPTCHAs, access controls, privacy controls, or platform rate limits. Never collect passwords, OTPs, session tokens, cookies, or private messages without authorization.

## Deployment requirements
- Keep `.env`, Telegram sessions, access tokens, cookies, and credentials out of source control.
- Use a long random `JWT_SECRET` and HTTPS in production.
- Restrict CORS to trusted origins.
- Use least-privilege, platform-approved permissions.
- Rotate compromised credentials and Telegram sessions immediately.
- Apply appropriate retention, deletion, and access controls to collected data.
- Monitor connector errors, authentication failures, and unusual traffic.

## Reporting
Do not publish credentials, tokens, private messages, or working exploit details in a public issue. Report security concerns privately through the repository owner's GitHub security reporting mechanism when available.
