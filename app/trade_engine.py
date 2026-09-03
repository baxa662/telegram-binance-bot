from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from binance_api import BinanceAPIError, execution_client, market_data_client
from config import settings
from database import (
    active_trade_for_symbol,
    close_trade,
    count_active_trades,
    create_pending_trade,
    get_trade,
    list_trades,
    update_trade,
)
from models import Signal
from notifier import error as notify_error
from notifier import sl_moved, tp_filled, trade_closed, trade_opened
from risk_manager import calculate_trade_plan

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


def _parse_dt(value: str):
    return datetime.fromisoformat(value)


def _price_crossed(direction: str, current: float, target: float, is_tp: bool) -> bool:
    if direction == "LONG":
        return current >= target if is_tp else current <= target
    return current <= target if is_tp else current >= target


def _entry_in_range(price: float, trade: dict) -> bool:
    low, high = float(trade["entry_min"]), float(trade["entry_max"])
    tolerance = settings.entry_range_tolerance_percent / 100.0
    low *= 1 - tolerance
    high *= 1 + tolerance
    return low <= price <= high


def _tp_allocations(count: int) -> list[float]:
    configured = settings.tp_allocations
    if len(configured) == count:
        return configured
    return [1.0 / count] * count


async def enqueue_signal(signal_id: int, signal: Signal) -> int | None:
    if settings.is_monitor:
        return None
    if count_active_trades() >= settings.max_open_trades:
        raise RuntimeError("MAX_OPEN_TRADES alcanzado")
    if not settings.allow_multiple_positions_per_symbol and active_trade_for_symbol(signal.symbol):
        raise RuntimeError(f"Ya existe un trade activo para {signal.symbol}")
    return create_pending_trade(signal_id, signal)


async def _account_balance() -> float:
    client = execution_client() if settings.is_testnet else market_data_client()
    # PAPER uses production account balance if credentials exist; otherwise caller can use 1000 fallback.
    try:
        data = await asyncio.to_thread(client.usdt_balance)
        return float(data["available"])
    except Exception:
        if settings.is_paper:
            return 1000.0
        raise


async def _open_trade(trade: dict, current_price: float):
    signal = Signal(
        symbol=trade["symbol"],
        direction=trade["direction"],
        entry_min=float(trade["entry_min"]),
        entry_max=float(trade["entry_max"]),
        take_profits=json.loads(trade["take_profits"]),
        stop_loss=float(trade["stop_loss"]),
        leverage=int(trade["leverage"]),
        margin_type="ISOLATED",
    )
    balance = await _account_balance()
    plan = calculate_trade_plan(
        signal,
        balance,
        settings.risk_percent,
        settings.max_leverage,
        settings.max_margin_percent,
        entry_price=current_price,
        ignore_risk_percent=settings.ignore_risk_percent,
    )
    client = execution_client()
    qty = await asyncio.to_thread(client.normalize_quantity, signal.symbol, plan.quantity, True)
    entry_price = await asyncio.to_thread(client.normalize_price, signal.symbol, current_price)
    sl = await asyncio.to_thread(client.normalize_price, signal.symbol, signal.stop_loss)
    tps = [await asyncio.to_thread(client.normalize_price, signal.symbol, tp) for tp in signal.take_profits]

    rules = await asyncio.to_thread(client.symbol_rules, signal.symbol)
    notional = qty * entry_price
    if rules.get("min_notional") and notional < rules["min_notional"]:
        raise RuntimeError(f"Notional {notional:.4f} < minimo {rules['min_notional']}")

    entry_order_id = None
    stop_order_id = None
    tp_order_ids: list[int | None] = []

    if settings.is_paper:
        pass
    else:
        if settings.is_production and not settings.live_orders_enabled:
            raise RuntimeError(
                "PRODUCTION bloqueado: ENABLE_PRODUCTION_TRADING=true y "
                "PRODUCTION_CONFIRMATION=I_UNDERSTAND_LIVE_TRADING requeridos"
            )
        await asyncio.to_thread(client.set_margin_type, signal.symbol, "ISOLATED")
        await asyncio.to_thread(client.set_leverage, signal.symbol, plan.leverage)
        entry_resp = await asyncio.to_thread(client.market_entry, signal.symbol, signal.direction, qty)
        entry_order_id = int(entry_resp.get("orderId")) if entry_resp.get("orderId") else None
        avg = float(entry_resp.get("avgPrice") or 0)
        if avg > 0:
            entry_price = avg

        stop_resp = await asyncio.to_thread(client.place_stop_close, signal.symbol, signal.direction, sl)
        stop_order_id = int(stop_resp["algoId"])

        allocations = _tp_allocations(len(tps))
        remaining = Decimal(str(qty))
        for idx, (tp, alloc) in enumerate(zip(tps, allocations)):
            if idx == len(tps) - 1:
                tp_qty = await asyncio.to_thread(
                    client.normalize_quantity, signal.symbol, float(remaining), True
                )
            else:
                tp_qty = await asyncio.to_thread(client.normalize_quantity, signal.symbol, qty * alloc, True)
                tp_qty = min(tp_qty, float(remaining))
            if tp_qty <= 0:
                tp_order_ids.append(None)
                continue
            resp = await asyncio.to_thread(client.place_take_profit, signal.symbol, signal.direction, tp, tp_qty)
            tp_order_ids.append(int(resp["algoId"]))
            remaining = max(Decimal("0"), remaining - Decimal(str(tp_qty)))

    update_trade(
        trade["id"],
        status="OPEN",
        entry_price=entry_price,
        quantity=qty,
        initial_quantity=qty,
        current_stop_loss=sl,
        take_profits=json.dumps(tps),
        leverage=plan.leverage,
        risk_percent=plan.risk_percent,
        risk_amount=plan.risk_amount,
        notional=qty * entry_price,
        margin_required=(qty * entry_price) / plan.leverage,
        entry_order_id=entry_order_id,
        stop_order_id=stop_order_id,
        tp_order_ids=json.dumps(tp_order_ids),
        tp_filled=json.dumps([False] * len(tps)),
        opened_at=_utcnow().isoformat(),
    )
    await trade_opened(get_trade(trade["id"]))


async def process_pending_entries():
    if settings.is_monitor:
        return
    client = market_data_client()
    for trade in list_trades(["PENDING_ENTRY"], limit=100):
        try:
            age = _utcnow() - _parse_dt(trade["created_at"])
            if age.total_seconds() > settings.signal_expiry_minutes * 60:
                close_trade(trade["id"], status="EXPIRED")
                await trade_closed(trade, "Señal expirada sin tocar entrada")
                continue
            if settings.entry_strategy != "MARKET_IF_IN_RANGE":
                raise RuntimeError(f"ENTRY_STRATEGY no soportada: {settings.entry_strategy}")
            price = await asyncio.to_thread(client.mark_price, trade["symbol"])
            if _entry_in_range(price, trade):
                await _open_trade(trade, price)
        except Exception as exc:
            logger.exception("Error procesando pending trade %s", trade["id"])
            await notify_error(f"Trade {trade['id']} {trade['symbol']}: {exc}")


async def _replace_stop(trade: dict, new_stop: float):
    client = execution_client()
    old = float(trade["current_stop_loss"])
    normalized = await asyncio.to_thread(client.normalize_price, trade["symbol"], new_stop)
    if abs(normalized - old) < 1e-15:
        return

    new_order_id = None
    if not settings.is_paper:
        old_id = trade.get("stop_order_id")
        if old_id:
            try:
                await asyncio.to_thread(client.cancel_algo_order, int(old_id))
            except Exception:
                logger.warning("No se pudo cancelar SL anterior %s", old_id, exc_info=True)
        resp = await asyncio.to_thread(client.place_stop_close, trade["symbol"], trade["direction"], normalized)
        new_order_id = int(resp["algoId"])

    update_trade(trade["id"], current_stop_loss=normalized, stop_order_id=new_order_id)
    await sl_moved(get_trade(trade["id"]), old, normalized)


async def _sync_live_trade(trade: dict):
    client = execution_client()
    position = await asyncio.to_thread(client.position, trade["symbol"])
    if not position:
        try:
            await asyncio.to_thread(client.cancel_all_open_orders, trade["symbol"])
        except Exception:
            logger.warning("No se pudieron cancelar ordenes al cerrar %s", trade["symbol"], exc_info=True)
        close_trade(trade["id"], status="CLOSED")
        await trade_closed(trade, "Posicion cerrada en Binance")
        return

    tps = json.loads(trade["take_profits"])
    filled = json.loads(trade["tp_filled"] or "[]")
    order_ids = json.loads(trade["tp_order_ids"] or "[]")
    changed = False
    for i, order_id in enumerate(order_ids):
        if i >= len(filled) or filled[i] or not order_id:
            continue
        order = await asyncio.to_thread(client.query_algo_order, int(order_id))
        if order.get("algoStatus") == "FINISHED":
            filled[i] = True
            changed = True
            await tp_filled(trade, i, tps[i])
            if i == 0 and settings.move_sl_to_breakeven_after_tp1:
                await _replace_stop(get_trade(trade["id"]), float(trade["entry_price"]))
            elif i == 1 and settings.move_sl_to_tp1_after_tp2 and len(tps) >= 1:
                await _replace_stop(get_trade(trade["id"]), float(tps[0]))
    if changed:
        update_trade(trade["id"], tp_filled=json.dumps(filled))


async def _sync_paper_trade(trade: dict):
    client = market_data_client()
    price = await asyncio.to_thread(client.mark_price, trade["symbol"])
    current_sl = float(trade["current_stop_loss"])
    if _price_crossed(trade["direction"], price, current_sl, is_tp=False):
        close_trade(trade["id"], status="CLOSED")
        await trade_closed(trade, f"SL virtual alcanzado @ {price}")
        return

    tps = json.loads(trade["take_profits"])
    filled = json.loads(trade["tp_filled"] or "[]")
    if not filled:
        filled = [False] * len(tps)
    changed = False
    for i, tp in enumerate(tps):
        if filled[i]:
            continue
        if _price_crossed(trade["direction"], price, float(tp), is_tp=True):
            filled[i] = True
            changed = True
            await tp_filled(trade, i, float(tp))
            if i == 0 and settings.move_sl_to_breakeven_after_tp1:
                await _replace_stop(get_trade(trade["id"]), float(trade["entry_price"]))
            elif i == 1 and settings.move_sl_to_tp1_after_tp2:
                await _replace_stop(get_trade(trade["id"]), float(tps[0]))
    if changed:
        update_trade(trade["id"], tp_filled=json.dumps(filled))
    if filled and all(filled):
        close_trade(trade["id"], status="CLOSED")
        await trade_closed(trade, "Todos los TP virtuales alcanzados")


async def process_open_trades():
    for trade in list_trades(["OPEN"], limit=100):
        try:
            if trade["mode"] == "PAPER":
                await _sync_paper_trade(trade)
            else:
                await _sync_live_trade(trade)
        except Exception as exc:
            logger.exception("Error sincronizando trade %s", trade["id"])
            await notify_error(f"Trade {trade['id']} {trade['symbol']}: {exc}")


async def pending_worker():
    while True:
        try:
            from database import is_paused
            if not is_paused():
                await process_pending_entries()
        except Exception:
            logger.exception("pending_worker fallo")
        await asyncio.sleep(settings.pending_entry_poll_seconds)


async def positions_worker():
    while True:
        try:
            await process_open_trades()
        except Exception:
            logger.exception("positions_worker fallo")
        await asyncio.sleep(settings.position_poll_seconds)


async def manual_breakeven(symbol: str) -> str:
    trade = active_trade_for_symbol(symbol.upper())
    if not trade or trade["status"] != "OPEN":
        return "No hay trade abierto para ese simbolo."
    await _replace_stop(trade, float(trade["entry_price"]))
    return f"SL de {symbol.upper()} movido a break-even."


async def manual_close(symbol: str) -> str:
    trade = active_trade_for_symbol(symbol.upper())
    if not trade or trade["status"] != "OPEN":
        return "No hay trade abierto para ese simbolo."
    if trade["mode"] == "PAPER":
        close_trade(trade["id"], status="CLOSED")
        await trade_closed(trade, "Cierre manual PAPER")
        return f"Paper trade {symbol.upper()} cerrado."
    client = execution_client()
    await asyncio.to_thread(client.cancel_all_open_orders, symbol.upper())
    await asyncio.to_thread(client.close_position_market, symbol.upper())
    close_trade(trade["id"], status="CLOSED")
    await trade_closed(trade, "Cierre manual")
    return f"Posicion {symbol.upper()} cerrada a mercado."
