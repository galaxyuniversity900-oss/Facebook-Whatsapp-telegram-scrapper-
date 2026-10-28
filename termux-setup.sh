#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

pkg install -y python
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  python - <<'PY'
from pathlib import Path
import secrets
p = Path(".env")
s = p.read_text()
s = s.replace("JWT_SECRET=replace-with-at-least-32-random-characters", "JWT_SECRET=" + secrets.token_hex(32))
s = s.replace("ADMIN_EMAIL=admin@example.com", "ADMIN_EMAIL=admin@termux.local")
s = s.replace("ADMIN_PASSWORD=change-this-immediately", "ADMIN_PASSWORD=" + secrets.token_urlsafe(24))
p.write_text(s)
p.chmod(0o600)
print("Created .env with a random JWT secret and administrator password.")
print("Administrator email: admin@termux.local")
print("Administrator password: " + next(x.split("=",1)[1] for x in s.splitlines() if x.startswith("ADMIN_PASSWORD=")))
PY
else
  chmod 600 .env
  echo ".env already exists; keeping your existing settings."
fi

mkdir -p data
echo
echo "Setup complete."
echo "Next: edit .env and set TELEGRAM_API_ID and TELEGRAM_API_HASH."
echo "Then run: bash termux-telegram-login.sh"
echo "Start the browser app with: bash termux-start.sh"
