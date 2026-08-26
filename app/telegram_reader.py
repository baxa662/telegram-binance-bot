import os
import logging
from telethon import TelegramClient, events

logger = logging.getLogger(__name__)

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]

SESSION_PATH = "/app/data/telegram"

client = TelegramClient(
    SESSION_PATH,
    API_ID,
    API_HASH
)

@client.on(events.NewMessage)
async def on_new_message(event):
    text = event.raw_text or ""

    logger.info("===== NUEVO MENSAJE TELEGRAM =====")
    logger.info(text)
    logger.info("==================================")


async def start_telegram():
    logger.info("Conectando con Telegram...")

    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError(
            "La sesion de Telegram no esta autorizada."
        )

    me = await client.get_me()

    logger.info(
        "Telegram conectado correctamente como %s",
        me.username or me.first_name
    )

    await client.run_until_disconnected()