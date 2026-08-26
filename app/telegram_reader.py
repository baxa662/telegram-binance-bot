import os
from telethon import TelegramClient, events

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

SESSION_PATH = "/app/data/telegram"

client = TelegramClient(
    SESSION_PATH,
    API_ID,
    API_HASH
)

@client.on(events.NewMessage)
async def new_message_handler(event):
    text = event.raw_text

    print("\n===== NUEVO MENSAJE =====")
    print(text)
    print("=========================\n")


async def start_telegram():
    await client.start()
    print("Telegram conectado")

    await client.run_until_disconnected()