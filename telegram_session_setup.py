"""Create a Hydrogram session string for an account the operator controls.

The session string is stored only in the local .env file; never share or commit it.
"""
import asyncio
import os
from pathlib import Path
from getpass import getpass

from hydrogram import Client


async def main() -> None:
    env_path = Path(".env")
    if not env_path.is_file():
        raise SystemExit("Missing .env. Run bash termux-setup.sh first.")

    api_id_text = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    if not api_id_text or not api_hash:
        raise SystemExit(
            "Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env, then run this script again."
        )
    try:
        api_id = int(api_id_text)
    except ValueError:
        raise SystemExit("TELEGRAM_API_ID must be an integer.")

    print("Telegram will send a login code to your own Telegram account.")
    print("Do not share the code or the generated session string.")
    client = Client("termux-telegram-login", api_id=api_id, api_hash=api_hash, in_memory=True)
    await client.start()
    try:
        session_string = await client.export_session_string()
    finally:
        await client.stop()

    lines = env_path.read_text().splitlines()
    updated = False
    output = []
    for line in lines:
        if line.startswith("TELEGRAM_SESSION="):
            output.append("TELEGRAM_SESSION=" + session_string)
            updated = True
        else:
            output.append(line)
    if not updated:
        output.append("TELEGRAM_SESSION=" + session_string)
    env_path.write_text("\n".join(output) + "\n")
    env_path.chmod(0o600)
    print("Telegram session saved locally in .env (permissions set to owner-only).")
    print("Now run: bash termux-start.sh")


if __name__ == "__main__":
    asyncio.run(main())
