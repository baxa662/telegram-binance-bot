from __future__ import annotations

import logging

from telethon import TelegramClient, events

from config import settings
from database import is_message_processed, mark_message_processed, save_signal
from notifier import error as notify_error
from notifier import signal_detected
from signal_parser import parse_signal
from trade_engine import enqueue_signal

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
        signal = parse_signal(text)
        mark_message_processed(chat_id, message_id)
        if signal is None:
            logger.info("Mensaje %s ignorado: no parece señal", message_id)
            return

        signal_id = save_signal(chat_id, message_id, signal, text)
        logger.info("Señal %s guardada: %s %s", signal_id, signal.symbol, signal.direction)
        await signal_detected(signal, settings.trading_mode)

        try:
            trade_id = await enqueue_signal(signal_id, signal)
            if trade_id:
                logger.info("Trade pendiente creado id=%s", trade_id)
        except Exception as exc:
            logger.warning("Señal guardada pero no encolada: %s", exc)
            await notify_error(f"Señal {signal.symbol}: {exc}")
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
