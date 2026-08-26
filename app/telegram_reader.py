import os
import logging

from notifier import send_signal_notification
from telethon import TelegramClient, events

from signal_parser import parse_signal
from database import (
    is_message_processed,
    mark_message_processed,
    save_signal,
)

logger = logging.getLogger(__name__)

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]

SOURCE_CHANNEL_ID = int(
    os.environ["TELEGRAM_SOURCE_CHANNEL_ID"]
)

SESSION_PATH = "/app/data/telegram"

client = TelegramClient(
    SESSION_PATH,
    API_ID,
    API_HASH
)


@client.on(events.NewMessage(chats=SOURCE_CHANNEL_ID))
async def on_signal_message(event):
    chat_id = event.chat_id
    message_id = event.id
    text = event.raw_text or ""

    logger.info(
        "Nuevo mensaje | chat_id=%s | message_id=%s",
        chat_id,
        message_id
    )

    if is_message_processed(
        chat_id,
        message_id
    ):
        logger.info(
            "Mensaje %s ya fue procesado. Ignorando.",
            message_id
        )
        return

    signal = parse_signal(text)

    if signal is None:
        logger.info(
            "El mensaje no parece una señal valida."
        )

        mark_message_processed(
            chat_id,
            message_id
        )

        return

    save_signal(
        chat_id=chat_id,
        message_id=message_id,
        signal=signal,
        raw_text=text
    )

    mark_message_processed(
        chat_id,
        message_id
    )

    await send_signal_notification(signal)

    logger.info("===== SENAL GUARDADA =====")
    logger.info("Symbol: %s", signal["symbol"])
    logger.info("Direction: %s", signal["direction"])
    logger.info(
        "Entry: %s - %s",
        signal["entry_min"],
        signal["entry_max"]
    )
    logger.info(
        "TPs: %s",
        signal["take_profits"]
    )
    logger.info(
        "SL: %s",
        signal["stop_loss"]
    )
    logger.info(
        "Leverage: %sx",
        signal["leverage"]
    )
    logger.info(
        "Margin: %s",
        signal["margin_type"]
    )
    logger.info("==========================")


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

    logger.info(
        "Escuchando canal ID: %s",
        SOURCE_CHANNEL_ID
    )

    await client.run_until_disconnected()