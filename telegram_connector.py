import os
from app import save_record

async def search_telegram(query: str, limit: int = 50) -> int:
    if not query or len(query) > 500:
        raise ValueError("query must contain 1-500 characters")
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session = os.getenv("TELEGRAM_SESSION")
    if not all((api_id, api_hash, session)):
        raise RuntimeError("TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_SESSION are required")
    from hydrogram import Client
    client = Client("socialintel", api_id=int(api_id), api_hash=api_hash, session_string=session)
    imported = 0
    await client.start()
    try:
        async for message in client.search_global(query, limit=min(limit, 100)):
            text = message.text or message.caption or ""
            chat_id = getattr(getattr(message, "chat", None), "id", "unknown")
            save_record({
                "source": "telegram",
                "external_id": f"{chat_id}:{message.id}",
                "author": getattr(getattr(message, "from_user", None), "username", None),
                "text": text,
            })
            imported += 1
    finally:
        await client.stop()
    return imported
