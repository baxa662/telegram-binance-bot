import os
import logging

from binance.um_futures import UMFutures
from decimal import Decimal, ROUND_DOWN

logger = logging.getLogger(__name__)

API_KEY = os.environ["BINANCE_API_KEY"]
API_SECRET = os.environ["BINANCE_API_SECRET"]

client = UMFutures(
    key=API_KEY,
    secret=API_SECRET,
)


def get_futures_balance():
    balances = client.balance()

    result = []

    for item in balances:
        balance = float(item["balance"])
        available = float(item["availableBalance"])

        if item["asset"] == "USDT" or balance > 0:
            result.append({
                "asset": item["asset"],
                "balance": balance,
                "available": available,
            })

    return result


def get_open_positions():
    positions = client.get_position_risk()

    result = []

    for position in positions:
        position_amount = float(position["positionAmt"])

        if position_amount == 0:
            continue

        result.append({
            "symbol": position["symbol"],
            "position_amount": position_amount,
            "entry_price": float(position["entryPrice"]),
            "mark_price": float(position["markPrice"]),
            "unrealized_profit": float(
                position["unRealizedProfit"]
            ),
            "leverage": int(position["leverage"]),
            "margin_type": position["marginType"],
        })

    return result

def get_usdt_balance():
    balances = client.balance()

    for item in balances:
        if item["asset"] == "USDT":
            return {
                "balance": float(item["balance"]),
                "available": float(item["availableBalance"]),
            }

    return {
        "balance": 0.0,
        "available": 0.0,
    }

def _floor_to_step(value: float, step: float) -> float:
    value_dec = Decimal(str(value))
    step_dec = Decimal(str(step))

    if step_dec == 0:
        return float(value_dec)

    floored = (value_dec / step_dec).to_integral_value(
        rounding=ROUND_DOWN
    ) * step_dec

    return float(floored)


def get_symbol_rules(symbol: str):
    exchange_info = client.exchange_info()

    for item in exchange_info["symbols"]:
        if item["symbol"] != symbol:
            continue

        rules = {
            "symbol": symbol,
            "price_precision": item.get("pricePrecision"),
            "quantity_precision": item.get("quantityPrecision"),
            "tick_size": None,
            "step_size": None,
            "min_qty": None,
            "min_notional": None,
        }

        for filter_item in item.get("filters", []):
            filter_type = filter_item.get("filterType")

            if filter_type == "PRICE_FILTER":
                rules["tick_size"] = float(
                    filter_item["tickSize"]
                )

            elif filter_type == "LOT_SIZE":
                rules["step_size"] = float(
                    filter_item["stepSize"]
                )
                rules["min_qty"] = float(
                    filter_item["minQty"]
                )

            elif filter_type == "MIN_NOTIONAL":
                rules["min_notional"] = float(
                    filter_item.get(
                        "notional",
                        filter_item.get("minNotional", 0)
                    )
                )

        return rules

    raise ValueError(
        f"El simbolo {symbol} no existe en Binance Futures."
    )


def normalize_order_values(
    symbol: str,
    quantity: float,
    entry_price: float,
    stop_loss: float,
    take_profits: list[float],
):
    rules = get_symbol_rules(symbol)

    if not rules["step_size"]:
        raise ValueError(
            f"No se encontro stepSize para {symbol}"
        )

    if not rules["tick_size"]:
        raise ValueError(
            f"No se encontro tickSize para {symbol}"
        )

    normalized_quantity = _floor_to_step(
        quantity,
        rules["step_size"]
    )

    normalized_entry = _floor_to_step(
        entry_price,
        rules["tick_size"]
    )

    normalized_sl = _floor_to_step(
        stop_loss,
        rules["tick_size"]
    )

    normalized_tps = [
        _floor_to_step(
            tp,
            rules["tick_size"]
        )
        for tp in take_profits
    ]

    if normalized_quantity < rules["min_qty"]:
        raise ValueError(
            f"Cantidad {normalized_quantity} menor "
            f"al minimo {rules['min_qty']} de {symbol}"
        )

    notional = normalized_quantity * normalized_entry

    if (
        rules["min_notional"]
        and notional < rules["min_notional"]
    ):
        raise ValueError(
            f"Notional {notional:.4f} menor al minimo "
            f"{rules['min_notional']} de {symbol}"
        )

    return {
        "quantity": normalized_quantity,
        "entry_price": normalized_entry,
        "stop_loss": normalized_sl,
        "take_profits": normalized_tps,
        "notional": notional,
        "rules": rules,
    }