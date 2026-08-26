import asyncio
import os

from telethon import TelegramClient


async def main():
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    path = os.getenv("TELEGRAM_SESSION_PATH", "/app/data/telegram")
    client = TelegramClient(path, api_id, api_hash)
    await client.start()
    me = await client.get_me()
    print(f"Sesion creada: {me.username or me.first_name} -> {path}.session")
    await client.disconnect()


asyncio.run(main())
