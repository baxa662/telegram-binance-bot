from __future__ import annotations

import logging
from dataclasses import dataclass

from config import settings
from database import save_signal
from models import Signal
from notifier import error as notify_error
from notifier import signal_detected
from signal_parser import parse_signal
from trade_engine import enqueue_signal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SignalProcessingResult:
    signal: Signal
    signal_id: int
    trade_id: int | None
    enqueue_error: str | None = None


async def process_signal_text(
    text: str, *, chat_id: int, message_id: int
) -> SignalProcessingResult | None:
    """Parse, persist and enqueue a signal received from any Telegram source."""
    signal = parse_signal(text)
    if signal is None:
        return None

    signal_id = save_signal(chat_id, message_id, signal, text)
    logger.info("Señal %s guardada: %s %s", signal_id, signal.symbol, signal.direction)
    await signal_detected(signal, settings.trading_mode)

    try:
        trade_id = await enqueue_signal(signal_id, signal)
        if trade_id:
            logger.info("Trade pendiente creado id=%s", trade_id)
        return SignalProcessingResult(signal, signal_id, trade_id)
    except Exception as exc:
        message = str(exc)
        logger.warning("Señal guardada pero no encolada: %s", message)
        await notify_error(f"Señal {signal.symbol}: {message}")
        return SignalProcessingResult(signal, signal_id, None, message)
