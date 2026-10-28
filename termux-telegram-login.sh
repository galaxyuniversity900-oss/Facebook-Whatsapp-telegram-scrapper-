#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  echo "Missing .env. Run: bash termux-setup.sh"
  exit 1
fi
set -a
. ./.env
set +a
. .venv/bin/activate
exec python telegram_session_setup.py
