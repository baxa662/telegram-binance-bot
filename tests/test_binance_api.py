import os


os.environ.setdefault("TELEGRAM_API_ID", "1")
os.environ.setdefault("TELEGRAM_API_HASH", "test")
os.environ.setdefault("TELEGRAM_SOURCE_CHANNEL_ID", "-1001")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1:test")
os.environ.setdefault("TELEGRAM_ADMIN_CHAT_ID", "1")

from app.binance_api import BinanceFuturesClient


def test_conditional_orders_use_algo_api(monkeypatch):
    client = BinanceFuturesClient(testnet=True)
    calls = []

    def fake_request(method, path, params=None, signed=False):
        calls.append((method, path, params, signed))
        return {"algoId": len(calls)}

    monkeypatch.setattr(client, "_request", fake_request)

    client.place_stop_close("ALGOUSDT", "LONG", 0.089824)
    client.place_take_profit("ALGOUSDT", "LONG", 0.093934, 100)

    assert calls[0] == (
        "POST",
        "/fapi/v1/algoOrder",
        {
            "symbol": "ALGOUSDT",
            "side": "SELL",
            "type": "STOP_MARKET",
            "triggerPrice": "0.089824",
            "closePosition": "true",
            "workingType": "MARK_PRICE",
            "priceProtect": "true",
            "algoType": "CONDITIONAL",
        },
        True,
    )
    assert calls[1][1] == "/fapi/v1/algoOrder"
    assert calls[1][2]["triggerPrice"] == "0.093934"
    assert calls[1][2]["reduceOnly"] == "true"
    assert "stopPrice" not in calls[0][2]
    assert "stopPrice" not in calls[1][2]


def test_algo_order_query_and_cancel(monkeypatch):
    client = BinanceFuturesClient(testnet=True)
    calls = []

    def fake_request(method, path, params=None, signed=False):
        calls.append((method, path, params, signed))
        return {}

    monkeypatch.setattr(client, "_request", fake_request)

    client.query_algo_order(123)
    client.cancel_algo_order(123)

    assert calls == [
        ("GET", "/fapi/v1/algoOrder", {"algoId": 123}, True),
        ("DELETE", "/fapi/v1/algoOrder", {"algoId": 123}, True),
    ]
