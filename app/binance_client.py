import os
import logging

from binance.um_futures import UMFutures

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