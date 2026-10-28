# Telegram on Android Termux (browser mode)

This repository is a Python/FastAPI service with a browser dashboard. It is not the Node/Electron WhatsApp Scrapper project; the steps below run this repository directly in Termux and keep the dashboard on the phone.

## 1. Install

From the repository directory in Termux:

```bash
bash termux-setup.sh
```

The setup creates a Python virtual environment and a private `.env` file. Keep the generated administrator password safe; do not paste it into chats or commit `.env`.

## 2. Configure Telegram API access

1. Sign in to the Telegram account you control and obtain your own API ID and API hash from Telegram's official developer portal.
2. Edit `.env` and fill in `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`.
3. Generate the local session:

```bash
bash termux-telegram-login.sh
```

Enter the login code (and two-step verification password if requested) only in your own Termux session. The resulting session string is written to `.env`. A session string grants account access: keep the file private and revoke the session from Telegram settings if it is exposed.

## 3. Start and open the dashboard

```bash
bash termux-start.sh
```

Open `http://127.0.0.1:8000` in the Android browser on the same phone. API docs are available at `http://127.0.0.1:8000/docs`; health is at `http://127.0.0.1:8000/health`.

Keep the Termux process running while using the dashboard. To stop it, press Ctrl+C in that Termux session. The service binds to loopback only and is not exposed to your Wi-Fi network.

## Notes and troubleshooting

- If installation fails, capture the full error from `python -m pip install -r requirements.txt`; Android/Termux package compatibility depends on Python and available wheels.
- If the dashboard reports Telegram is not configured, verify the three `TELEGRAM_*` variables in `.env` and restart the service.
- Telegram global search is limited by the account, Telegram's own search behavior, and API limits. It is not a private-chat bypass or a way to access groups/channels you cannot access.
- The existing backend uses SQLite by default in `socialintel.db`; back up this database and `.env` securely. Never commit either file.
- This setup does not claim that tests or an on-device Termux run have passed; verify on the target phone after installation.
