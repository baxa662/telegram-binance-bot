import os


os.environ.setdefault("TELEGRAM_API_ID", "1")
os.environ.setdefault("TELEGRAM_API_HASH", "test")
os.environ.setdefault("TELEGRAM_SOURCE_CHANNEL_ID", "-1001")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1:test")
os.environ.setdefault("TELEGRAM_ADMIN_CHAT_ID", "1")

from app.binance_api import BinanceFuturesClient


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_signed_request_syncs_time_and_retries_once_on_1021(monkeypatch):
    client = BinanceFuturesClient(testnet=True)
    client.api_key = "key"
    client.api_secret = "secret"
    responses = iter(
        [
            FakeResponse(400, {"code": -1021, "msg": "Timestamp ahead"}),
            FakeResponse(200, {"serverTime": 1_000_500}),
            FakeResponse(200, {"ok": True}),
        ]
    )
    calls = []

    def fake_session_request(**kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(client.session, "request", fake_session_request)
    monkeypatch.setattr("app.binance_api.time.time", lambda: 1000.0)

    result = client._request("POST", "/fapi/v1/leverage", {"symbol": "BTCUSDT"}, signed=True)

    assert result == {"ok": True}
    assert [call["url"] for call in calls] == [
        "https://testnet.binancefuture.com/fapi/v1/leverage",
        "https://testnet.binancefuture.com/fapi/v1/time",
        "https://testnet.binancefuture.com/fapi/v1/leverage",
    ]
    assert calls[0]["params"]["timestamp"] == 1_000_000
    assert calls[2]["params"]["timestamp"] == 1_000_500


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
