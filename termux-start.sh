#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Missing .venv. Run: bash termux-setup.sh"
  exit 1
fi
if [ ! -f .env ]; then
  echo "Missing .env. Run: bash termux-setup.sh"
  exit 1
fi

set -a
. ./.env
set +a
. .venv/bin/activate

echo "Telegram-enabled dashboard: http://127.0.0.1:8000"
echo "Health check: http://127.0.0.1:8000/health"
echo "API docs: http://127.0.0.1:8000/docs"
exec python -m uvicorn app:app --host 127.0.0.1 --port 8000
