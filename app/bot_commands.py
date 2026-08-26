from __future__ import annotations

import asyncio
import json
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from binance_api import execution_client, market_data_client
from config import settings
from database import (
    get_last_signal,
    get_recent_signals,
    is_paused,
    list_trades,
    set_paused,
)
from trade_engine import manual_breakeven, manual_close

logger = logging.getLogger(__name__)


def _authorized(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.id == settings.telegram_admin_chat_id)


async def _guard(update: Update) -> bool:
    if _authorized(update):
        return True
    if update.message:
        await update.message.reply_text("No autorizado.")
    return False


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update): return
    live = "habilitado" if settings.live_orders_enabled else "bloqueado"
    await update.message.reply_text(
        f"Estado\n\nModo: {settings.trading_mode}\nPausado: {'SI' if is_paused() else 'NO'}\n"
        f"Produccion live: {live}\nCanal: {settings.telegram_source_channel_id}"
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update): return
    try:
        client = execution_client() if settings.is_testnet else market_data_client()
        balance = await asyncio.to_thread(client.usdt_balance)
        await update.message.reply_text(
            f"Balance USDT\nTotal: {balance['balance']:.4f}\nDisponible: {balance['available']:.4f}"
        )
    except Exception as exc:
        await update.message.reply_text(f"Error Binance: {exc}")


async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update): return
    if settings.is_paper:
        trades = list_trades(["OPEN"], 20)
        if not trades:
            await update.message.reply_text("No hay paper trades abiertos.")
            return
        lines = ["Paper trades abiertos", ""]
        for t in trades:
            lines.append(f"#{t['id']} {t['symbol']} {t['direction']} | entry {t['entry_price']} | SL {t['current_stop_loss']}")
        await update.message.reply_text("\n".join(lines))
        return
    try:
        client = execution_client()
        positions = await asyncio.to_thread(client.open_positions)
        if not positions:
            await update.message.reply_text("No hay posiciones abiertas.")
            return
        lines = ["Posiciones Binance", ""]
        for p in positions:
            direction = "LONG" if float(p["positionAmt"]) > 0 else "SHORT"
            lines.extend([
                f"{p['symbol']} {direction}",
                f"Qty: {p['positionAmt']}",
                f"Entry: {p['entryPrice']}",
                f"Mark: {p.get('markPrice', '?')}",
                f"PnL: {p.get('unRealizedProfit', '?')}",
                "",
            ])
        await update.message.reply_text("\n".join(lines)[:4000])
    except Exception as exc:
        await update.message.reply_text(f"Error Binance: {exc}")


async def lastsignal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update): return
    s = get_last_signal()
    if not s:
        await update.message.reply_text("No hay señales guardadas.")
        return
    await update.message.reply_text(
        f"Ultima señal\n\n{s['symbol']} {s['direction']}\n"
        f"Entrada: {s['entry_min']} - {s['entry_max']}\nTPs: {s['take_profits']}\n"
        f"SL: {s['stop_loss']}\nLeverage: x{s['leverage']}"
    )


async def signals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update): return
    rows = get_recent_signals(5)
    if not rows:
        await update.message.reply_text("No hay señales guardadas.")
        return
    await update.message.reply_text("\n".join(["Ultimas señales", ""] + [f"#{r['id']} {r['symbol']} {r['direction']} x{r['leverage']}" for r in rows]))


async def trades_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update): return
    rows = list_trades(None, 10)
    if not rows:
        await update.message.reply_text("No hay trades guardados.")
        return
    lines = ["Ultimos trades", ""]
    for t in rows:
        lines.append(f"#{t['id']} [{t['mode']}] {t['symbol']} {t['direction']} - {t['status']}")
    await update.message.reply_text("\n".join(lines))


async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update): return
    set_paused(True)
    await update.message.reply_text("Bot pausado. No abrira nuevas operaciones; seguira gestionando las abiertas.")


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update): return
    set_paused(False)
    await update.message.reply_text("Bot reanudado.")


async def breakeven_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update): return
    if not settings.allow_manual_breakeven:
        await update.message.reply_text("Comando deshabilitado por configuracion.")
        return
    if not context.args:
        await update.message.reply_text("Uso: /breakeven BTCUSDT")
        return
    try:
        await update.message.reply_text(await manual_breakeven(context.args[0].upper()))
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def close_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update): return
    if not settings.allow_manual_close:
        await update.message.reply_text("Comando deshabilitado por configuracion.")
        return
    if not context.args:
        await update.message.reply_text("Uso: /close BTCUSDT")
        return
    try:
        await update.message.reply_text(await manual_close(context.args[0].upper()))
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


def build_bot_application() -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()
    for name, fn in [
        ("status", status_command),
        ("balance", balance_command),
        ("positions", positions_command),
        ("lastsignal", lastsignal_command),
        ("signals", signals_command),
        ("trades", trades_command),
        ("pause", pause_command),
        ("resume", resume_command),
        ("breakeven", breakeven_command),
        ("close", close_command),
    ]:
        app.add_handler(CommandHandler(name, fn))
    return app


async def start_bot_commands():
    app = build_bot_application()
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=False)
    logger.info("Bot de comandos iniciado")
    return app
