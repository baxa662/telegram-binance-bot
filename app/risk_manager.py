def calculate_trade_plan(
    signal: dict,
    account_balance: float,
    risk_percent: float = 1.0,
):
    entry_price = (
        signal["entry_min"] + signal["entry_max"]
    ) / 2

    stop_loss = signal["stop_loss"]

    risk_amount = account_balance * (
        risk_percent / 100
    )

    if signal["direction"] == "LONG":
        stop_distance = entry_price - stop_loss
    else:
        stop_distance = stop_loss - entry_price

    if stop_distance <= 0:
        raise ValueError("Stop loss invalido para la direccion")

    quantity = risk_amount / stop_distance

    notional = quantity * entry_price

    margin_required = notional / signal["leverage"]

    return {
        "symbol": signal["symbol"],
        "direction": signal["direction"],
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profits": signal["take_profits"],
        "leverage": signal["leverage"],
        "risk_percent": risk_percent,
        "risk_amount": risk_amount,
        "quantity": quantity,
        "notional": notional,
        "margin_required": margin_required,
    }