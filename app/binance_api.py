from __future__ import annotations

import hashlib
import hmac
import logging
import time
from decimal import Decimal, ROUND_DOWN
from typing import Any
from urllib.parse import urlencode

import requests

from config import settings

logger = logging.getLogger(__name__)


class BinanceAPIError(RuntimeError):
    pass


def _decimal_str(value: float | Decimal) -> str:
    d = Decimal(str(value)).normalize()
    return format(d, "f")


def floor_to_step(value: float, step: float) -> float:
    v = Decimal(str(value))
    s = Decimal(str(step))
    if s <= 0:
        return float(v)
    return float((v / s).to_integral_value(rounding=ROUND_DOWN) * s)


class BinanceFuturesClient:
    def __init__(self, testnet: bool = False):
        self.testnet = testnet
        self.base_url = (
            "https://testnet.binancefuture.com"
            if testnet
            else "https://fapi.binance.com"
        )
        self.api_key = settings.binance_testnet_api_key if testnet else settings.binance_api_key
        self.api_secret = settings.binance_testnet_api_secret if testnet else settings.binance_api_secret
        self.timeout = settings.binance_timeout_seconds
        self.recv_window = settings.binance_recv_window
        self.session = requests.Session()
        self.time_offset_ms = 0
        self._exchange_info_cache: dict[str, Any] | None = None
        self._exchange_info_cached_at = 0.0

    def _headers(self) -> dict[str, str]:
        return {"X-MBX-APIKEY": self.api_key} if self.api_key else {}

    def _request(self, method: str, path: str, params: dict | None = None, signed: bool = False):
        params = dict(params or {})
        if signed:
            if not self.api_key or not self.api_secret:
                raise BinanceAPIError("API key/secret no configurados para este entorno")
            params["timestamp"] = int(time.time() * 1000) + self.time_offset_ms
            params["recvWindow"] = self.recv_window
            query = urlencode(params, doseq=True)
            signature = hmac.new(
                self.api_secret.encode("utf-8"),
                query.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            params["signature"] = signature

        url = f"{self.base_url}{path}"
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        try:
            payload = response.json()
        except Exception:
            payload = response.text

        if response.status_code >= 400:
            raise BinanceAPIError(f"HTTP {response.status_code}: {payload}")
        if isinstance(payload, dict) and isinstance(payload.get("code"), int) and payload["code"] < 0:
            raise BinanceAPIError(str(payload))
        return payload

    def sync_time(self) -> None:
        payload = self._request("GET", "/fapi/v1/time")
        self.time_offset_ms = int(payload["serverTime"]) - int(time.time() * 1000)

    def ping(self) -> bool:
        self._request("GET", "/fapi/v1/ping")
        return True

    def exchange_info(self) -> dict:
        now = time.time()
        if self._exchange_info_cache and now - self._exchange_info_cached_at < 3600:
            return self._exchange_info_cache
        data = self._request("GET", "/fapi/v1/exchangeInfo")
        self._exchange_info_cache = data
        self._exchange_info_cached_at = now
        return data

    def symbol_rules(self, symbol: str) -> dict:
        for item in self.exchange_info().get("symbols", []):
            if item.get("symbol") != symbol:
                continue
            rules = {
                "symbol": symbol,
                "status": item.get("status"),
                "tick_size": None,
                "step_size": None,
                "market_step_size": None,
                "min_qty": None,
                "min_notional": 0.0,
            }
            for f in item.get("filters", []):
                ft = f.get("filterType")
                if ft == "PRICE_FILTER":
                    rules["tick_size"] = float(f["tickSize"])
                elif ft == "LOT_SIZE":
                    rules["step_size"] = float(f["stepSize"])
                    rules["min_qty"] = float(f["minQty"])
                elif ft == "MARKET_LOT_SIZE":
                    rules["market_step_size"] = float(f["stepSize"])
                elif ft in {"MIN_NOTIONAL", "NOTIONAL"}:
                    rules["min_notional"] = float(f.get("notional") or f.get("minNotional") or 0)
            return rules
        raise BinanceAPIError(f"Simbolo {symbol} no encontrado")

    def normalize_quantity(self, symbol: str, quantity: float, market: bool = True) -> float:
        rules = self.symbol_rules(symbol)
        step = rules["market_step_size"] if market and rules.get("market_step_size") else rules["step_size"]
        qty = floor_to_step(quantity, step)
        if rules.get("min_qty") is not None and qty < rules["min_qty"]:
            raise BinanceAPIError(f"Cantidad {qty} menor a minQty {rules['min_qty']} para {symbol}")
        return qty

    def normalize_price(self, symbol: str, price: float) -> float:
        tick = self.symbol_rules(symbol)["tick_size"]
        return floor_to_step(price, tick)

    def mark_price(self, symbol: str) -> float:
        data = self._request("GET", "/fapi/v1/premiumIndex", {"symbol": symbol})
        return float(data["markPrice"])

    def balance(self) -> list[dict]:
        try:
            return self._request("GET", "/fapi/v2/balance", signed=True)
        except BinanceAPIError as exc:
            if "-1021" in str(exc):
                self.sync_time()
                return self._request("GET", "/fapi/v2/balance", signed=True)
            raise

    def usdt_balance(self) -> dict:
        for item in self.balance():
            if item.get("asset") == "USDT":
                return {
                    "balance": float(item.get("balance", 0)),
                    "available": float(item.get("availableBalance", 0)),
                }
        return {"balance": 0.0, "available": 0.0}

    def positions(self, symbol: str | None = None) -> list[dict]:
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/fapi/v2/positionRisk", params, signed=True)

    def open_positions(self) -> list[dict]:
        return [p for p in self.positions() if abs(float(p.get("positionAmt", 0))) > 0]

    def position(self, symbol: str) -> dict | None:
        for p in self.positions(symbol):
            if p.get("symbol") == symbol and abs(float(p.get("positionAmt", 0))) > 0:
                return p
        return None

    def set_leverage(self, symbol: str, leverage: int) -> dict:
        return self._request("POST", "/fapi/v1/leverage", {"symbol": symbol, "leverage": leverage}, signed=True)

    def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED") -> None:
        try:
            self._request("POST", "/fapi/v1/marginType", {"symbol": symbol, "marginType": margin_type}, signed=True)
        except BinanceAPIError as exc:
            # -4046 = "No need to change margin type."
            if "-4046" not in str(exc):
                raise

    def new_order(self, **params) -> dict:
        return self._request("POST", "/fapi/v1/order", params, signed=True)

    def new_algo_order(self, **params) -> dict:
        params.setdefault("algoType", "CONDITIONAL")
        return self._request("POST", "/fapi/v1/algoOrder", params, signed=True)

    def market_entry(self, symbol: str, direction: str, quantity: float) -> dict:
        side = "BUY" if direction == "LONG" else "SELL"
        return self.new_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=_decimal_str(quantity),
            newOrderRespType="RESULT",
        )

    def place_stop_close(self, symbol: str, direction: str, stop_price: float) -> dict:
        side = "SELL" if direction == "LONG" else "BUY"
        return self.new_algo_order(
            symbol=symbol,
            side=side,
            type="STOP_MARKET",
            triggerPrice=_decimal_str(stop_price),
            closePosition="true",
            workingType="MARK_PRICE",
            priceProtect="true",
        )

    def place_take_profit(self, symbol: str, direction: str, stop_price: float, quantity: float) -> dict:
        side = "SELL" if direction == "LONG" else "BUY"
        return self.new_algo_order(
            symbol=symbol,
            side=side,
            type="TAKE_PROFIT_MARKET",
            triggerPrice=_decimal_str(stop_price),
            quantity=_decimal_str(quantity),
            reduceOnly="true",
            workingType="MARK_PRICE",
            priceProtect="true",
        )

    def query_order(self, symbol: str, order_id: int) -> dict:
        return self._request("GET", "/fapi/v1/order", {"symbol": symbol, "orderId": order_id}, signed=True)

    def query_algo_order(self, algo_id: int) -> dict:
        return self._request("GET", "/fapi/v1/algoOrder", {"algoId": algo_id}, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        return self._request("DELETE", "/fapi/v1/order", {"symbol": symbol, "orderId": order_id}, signed=True)

    def cancel_algo_order(self, algo_id: int) -> dict:
        return self._request("DELETE", "/fapi/v1/algoOrder", {"algoId": algo_id}, signed=True)

    def cancel_all_algo_open_orders(self, symbol: str) -> dict:
        return self._request("DELETE", "/fapi/v1/algoOpenOrders", {"symbol": symbol}, signed=True)

    def cancel_all_open_orders(self, symbol: str) -> dict:
        regular = self._request("DELETE", "/fapi/v1/allOpenOrders", {"symbol": symbol}, signed=True)
        algo = self.cancel_all_algo_open_orders(symbol)
        return {"regular": regular, "algo": algo}

    def close_position_market(self, symbol: str) -> dict | None:
        pos = self.position(symbol)
        if not pos:
            return None
        amt = float(pos["positionAmt"])
        if amt == 0:
            return None
        side = "SELL" if amt > 0 else "BUY"
        qty = self.normalize_quantity(symbol, abs(amt), market=True)
        return self.new_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=_decimal_str(qty),
            reduceOnly="true",
            newOrderRespType="RESULT",
        )


PROD_CLIENT = BinanceFuturesClient(testnet=False)
TESTNET_CLIENT = BinanceFuturesClient(testnet=True)


def execution_client() -> BinanceFuturesClient:
    return TESTNET_CLIENT if settings.is_testnet else PROD_CLIENT


def market_data_client() -> BinanceFuturesClient:
    # Use production market prices in MONITOR/PAPER/PRODUCTION, testnet prices in TESTNET.
    return TESTNET_CLIENT if settings.is_testnet else PROD_CLIENT
