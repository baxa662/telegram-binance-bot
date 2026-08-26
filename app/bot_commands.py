import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from database import (
    get_last_signal,
    get_recent_signals,
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["TELEGRAM_ADMIN_CHAT_ID"])

TRADING_MODE = os.getenv(
    "TRADING_MODE",
    "MONITOR"
)


def is_admin(update: Update) -> bool:
    if update.effective_chat is None:
        return False

    return update.effective_chat.id == ADMIN_CHAT_ID


async def deny_if_not_admin(update: Update) -> bool:
    if is_admin(update):
        return False

    if update.message:
        await update.message.reply_text(
            "No autorizado."
        )

    return True


async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if await deny_if_not_admin(update):
        return

    message = (
        "Estado del bot\n\n"
        "Telegram Reader: activo\n"
        "Parser: activo\n"
        "Base de datos: activa\n"
        f"Trading mode: {TRADING_MODE}\n\n"
        "Binance: no conectado"
    )

    await update.message.reply_text(message)


async def lastsignal_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if await deny_if_not_admin(update):
        return

    signal = get_last_signal()

    if signal is None:
        await update.message.reply_text(
            "No hay señales guardadas."
        )
        return

    message = (
        "Ultima señal\n\n"
        f"Par: {signal['symbol']}\n"
        f"Dirección: {signal['direction']}\n"
        f"Entrada: {signal['entry_min']} - {signal['entry_max']}\n"
        f"TPs: {signal['take_profits']}\n"
        f"SL: {signal['stop_loss']}\n"
        f"Apalancamiento: x{signal['leverage']}\n"
        f"Margen: {signal['margin_type']}\n"
        f"Message ID: {signal['message_id']}"
    )

    await update.message.reply_text(message)


async def signals_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if await deny_if_not_admin(update):
        return

    signals = get_recent_signals(limit=5)

    if not signals:
        await update.message.reply_text(
            "No hay señales guardadas."
        )
        return

    lines = [
        "Ultimas señales",
        ""
    ]

    for signal in signals:
        lines.append(
            f"{signal['symbol']} | "
            f"{signal['direction']} | "
            f"x{signal['leverage']} | "
            f"SL {signal['stop_loss']}"
        )

    await update.message.reply_text(
        "\n".join(lines)
    )


def build_bot_application():
    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "status",
            status_command
        )
    )

    application.add_handler(
        CommandHandler(
            "lastsignal",
            lastsignal_command
        )
    )

    application.add_handler(
        CommandHandler(
            "signals",
            signals_command
        )
    )

    return application


async def start_bot_commands():
    logger.info(
        "Iniciando bot de comandos..."
    )

    application = build_bot_application()

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    logger.info(
        "Bot de comandos iniciado."
    )

    return application