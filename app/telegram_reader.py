from __future__ import annotations

import logging

from telethon import TelegramClient, events

from config import settings
from database import is_message_processed, mark_message_processed
from notifier import error as notify_error
from signal_processor import process_signal_text

logger = logging.getLogger(__name__)

client = TelegramClient(
    settings.telegram_session_path,
    settings.telegram_api_id,
    settings.telegram_api_hash,
)


@client.on(events.NewMessage(chats=settings.telegram_source_channel_id))
async def on_signal_message(event):
    chat_id = int(event.chat_id)
    message_id = int(event.id)
    text = event.raw_text or ""

    if is_message_processed(chat_id, message_id):
        return

    try:
        mark_message_processed(chat_id, message_id)
        result = await process_signal_text(text, chat_id=chat_id, message_id=message_id)
        if result is None:
            logger.info("Mensaje %s ignorado: no parece señal", message_id)
    except Exception as exc:
        logger.exception("Error procesando mensaje Telegram")
        await notify_error(f"Mensaje {message_id}: {exc}")


async def start_telegram_reader():
    logger.info("Conectando Telethon...")
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Sesion Telethon no autorizada. Ejecuta scripts/create_telegram_session.py")
    me = await client.get_me()
    logger.info("Telethon conectado como %s. Canal=%s", me.username or me.first_name, settings.telegram_source_channel_id)
    await client.run_until_disconnected()
