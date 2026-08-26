import os
import logging

from telegram import Bot

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["TELEGRAM_ADMIN_CHAT_ID"])

bot = Bot(token=BOT_TOKEN)


async def send_signal_notification(signal: dict):
    tps = "\n".join(
        f"TP{i + 1}: {value}"
        for i, value in enumerate(signal["take_profits"])
    )

    message = (
        "Nueva señal detectada\n\n"
        f"Par: {signal['symbol']}\n"
        f"Dirección: {signal['direction']}\n"
        f"Entrada: {signal['entry_min']} - {signal['entry_max']}\n"
        f"{tps}\n"
        f"SL: {signal['stop_loss']}\n"
        f"Apalancamiento: x{signal['leverage']}\n"
        f"Margen: {signal['margin_type']}\n\n"
        "Modo actual: MONITOR\n"
        "No se ejecutó ninguna operación."
    )

    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message
        )

        logger.info(
            "Notificacion enviada a Telegram."
        )

    except Exception:
        logger.exception(
            "Error enviando notificacion por Telegram."
        )

async def send_paper_trade_notification(trade: dict):
    tps = "\n".join(
        f"TP{i + 1}: {value}"
        for i, value in enumerate(trade["take_profits"])
    )

    message = (
        "PAPER TRADE CREADO\n\n"
        f"Par: {trade['symbol']}\n"
        f"Direccion: {trade['direction']}\n"
        f"Entrada: {trade['entry_price']}\n"
        f"Cantidad: {trade['quantity']}\n"
        f"{tps}\n"
        f"SL: {trade['stop_loss']}\n"
        f"Leverage: x{trade['leverage']}\n"
        f"Riesgo: {trade['risk_percent']:.2f}%\n"
        f"Riesgo monetario: {trade['risk_amount']:.2f} USDT\n"
        f"Margen estimado: {trade['margin_required']:.2f} USDT\n\n"
        "SIMULACION - no se envio ninguna orden real."
    )

    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=message
    )