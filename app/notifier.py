from __future__ import annotations

import logging

from telegram import Bot

from config import settings
from models import Signal

logger = logging.getLogger(__name__)
bot = Bot(settings.telegram_bot_token)


async def send(text: str):
    try:
        await bot.send_message(chat_id=settings.telegram_admin_chat_id, text=text)
    except Exception:
        logger.exception("No se pudo enviar notificacion")


async def signal_detected(signal: Signal, mode: str):
    tps = "\n".join(f"TP{i+1}: {tp}" for i, tp in enumerate(signal.take_profits))
    await send(
        f"Nueva señal detectada\n\n"
        f"{signal.symbol} {signal.direction}\n"
        f"Entrada: {signal.entry_min} - {signal.entry_max}\n"
        f"{tps}\nSL: {signal.stop_loss}\n"
        f"Leverage señal: x{signal.leverage}\n"
        f"Modo: {mode}"
    )


async def trade_opened(trade: dict):
    await send(
        f"OPERACION ABIERTA [{trade['mode']}]\n\n"
        f"{trade['symbol']} {trade['direction']}\n"
        f"Entrada: {trade['entry_price']}\nCantidad: {trade['quantity']}\n"
        f"SL: {trade['current_stop_loss']}\nLeverage: x{trade['leverage']}\n"
        f"Riesgo: {trade.get('risk_amount', 0):.2f} USDT"
    )


async def tp_filled(trade: dict, index: int, price: float):
    await send(f"TP{index+1} alcanzado\n{trade['symbol']} {trade['direction']}\nPrecio: {price}")


async def sl_moved(trade: dict, old: float, new: float):
    await send(f"SL movido\n{trade['symbol']}\n{old} -> {new}")


async def trade_closed(trade: dict, reason: str):
    await send(f"OPERACION CERRADA [{trade['mode']}]\n{trade['symbol']}\nMotivo: {reason}")


async def error(text: str):
    await send(f"ERROR\n{text}")
