from __future__ import annotations

from models import Signal, TradePlan


def calculate_trade_plan(
    signal: Signal,
    account_balance: float,
    risk_percent: float,
    max_leverage: int,
    max_margin_percent: float,
    entry_price: float | None = None,
    ignore_risk_percent: bool = False,
) -> TradePlan:
    if account_balance <= 0:
        raise ValueError("Balance disponible invalido")

    leverage = min(signal.leverage, max_leverage)
    entry = entry_price if entry_price is not None else (signal.entry_min + signal.entry_max) / 2
    stop_distance = (
        entry - signal.stop_loss
        if signal.direction == "LONG"
        else signal.stop_loss - entry
    )
    if stop_distance <= 0:
        raise ValueError("SL invalido para la direccion")

    risk_amount = account_balance * (risk_percent / 100.0)
    quantity_by_risk = risk_amount / stop_distance

    max_margin = account_balance * (max_margin_percent / 100.0)
    max_notional = max_margin * leverage
    quantity_by_margin = max_notional / entry

    quantity = quantity_by_margin if ignore_risk_percent else min(quantity_by_risk, quantity_by_margin)
    if quantity <= 0:
        raise ValueError("Cantidad calculada invalida")

    notional = quantity * entry
    margin_required = notional / leverage

    return TradePlan(
        symbol=signal.symbol,
        direction=signal.direction,
        entry_price=entry,
        stop_loss=signal.stop_loss,
        take_profits=signal.take_profits,
        leverage=leverage,
        quantity=quantity,
        risk_percent=risk_percent,
        risk_amount=risk_amount,
        notional=notional,
        margin_required=margin_required,
    )
