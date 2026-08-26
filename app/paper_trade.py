import logging

from binance_client import (
    get_usdt_balance,
    normalize_order_values,
)
from risk_manager import calculate_trade_plan

logger = logging.getLogger(__name__)


def build_paper_trade(signal: dict):
    balance = get_usdt_balance()

    if balance["available"] <= 0:
        raise ValueError(
            "No hay USDT disponibles en Futures."
        )

    plan = calculate_trade_plan(
        signal=signal,
        account_balance=balance["available"],
        risk_percent=1.0,
    )

    normalized = normalize_order_values(
        symbol=plan["symbol"],
        quantity=plan["quantity"],
        entry_price=plan["entry_price"],
        stop_loss=plan["stop_loss"],
        take_profits=plan["take_profits"],
    )

    return {
        "symbol": plan["symbol"],
        "direction": plan["direction"],
        "entry_price": normalized["entry_price"],
        "quantity": normalized["quantity"],
        "stop_loss": normalized["stop_loss"],
        "take_profits": normalized["take_profits"],
        "leverage": plan["leverage"],
        "risk_percent": plan["risk_percent"],
        "risk_amount": plan["risk_amount"],
        "notional": normalized["notional"],
        "margin_required": (
            normalized["notional"]
            / plan["leverage"]
        ),
        "status": "PAPER_OPEN",
    }