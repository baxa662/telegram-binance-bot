from __future__ import annotations

import asyncio
import json
import logging

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from binance_api import execution_client, market_data_client
from config import settings
from database import (
    get_last_signal,
    get_recent_signals,
    is_paused,
    list_trades,
    set_paused,
)
from signal_processor import process_signal_text
from trade_engine import manual_breakeven, manual_close

logger = logging.getLogger(__name__)

WAITING_MANUAL_SIGNAL = 1

BOT_COMMANDS = (
    ("help", "Muestra todos los comandos disponibles"),
    ("status", "Muestra el modo y estado del bot"),
    ("balance", "Consulta el balance disponible en USDT"),
    ("positions", "Lista las posiciones abiertas"),
    ("lastsignal", "Muestra la ultima señal guardada"),
    ("signals", "Lista las ultimas señales recibidas"),
    ("trades", "Lista los ultimos trades del bot"),
    ("pause", "Pausa la apertura de nuevas operaciones"),
    ("resume", "Reanuda la apertura de operaciones"),
    ("exec_signal", "Permite cargar una señal manualmente"),
    ("breakeven", "Mueve el SL a entrada: /breakeven BTCUSDT"),
    ("close", "Cierra una posicion: /close BTCUSDT"),
    ("cancel", "Cancela la carga de una señal manual"),
)


def _authorized(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.id == settings.telegram_admin_chat_id)


async def _guard(update: Update) -> bool:
    if _authorized(update):
        return True
    if update.message:
        await update.message.reply_text("No autorizado.")
    return False


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    lines = ["Comandos disponibles", ""]
    lines.extend(f"/{name} - {description}" for name, description in BOT_COMMANDS)
    await update.message.reply_text("\n".join(lines))


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


async def exec_signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "Envia ahora el texto completo de la señal. Usare el parser normal del bot.\n\n"
        "Puedes cancelar con /cancel."
    )
    return WAITING_MANUAL_SIGNAL


async def receive_manual_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return ConversationHandler.END

    try:
        result = await process_signal_text(
            update.message.text or "",
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
        )
    except Exception as exc:
        logger.exception("Error procesando señal manual")
        await update.message.reply_text(f"No pude procesar la señal: {exc}")
        return ConversationHandler.END

    if result is None:
        await update.message.reply_text(
            "No pude reconocer una señal valida. Revisa simbolo, LONG/SHORT, entrada, "
            "al menos un TP, SL y vuelve a enviarla; o usa /cancel."
        )
        return WAITING_MANUAL_SIGNAL

    if result.enqueue_error:
        await update.message.reply_text(
            f"Señal #{result.signal_id} guardada, pero no se pudo encolar: "
            f"{result.enqueue_error}"
        )
    elif result.trade_id:
        await update.message.reply_text(
            f"Señal #{result.signal_id} aceptada. Trade pendiente #{result.trade_id}: "
            f"{result.signal.symbol} {result.signal.direction}."
        )
    else:
        await update.message.reply_text(
            f"Señal #{result.signal_id} guardada: {result.signal.symbol} "
            f"{result.signal.direction}. Modo MONITOR: no se creo un trade."
        )
    return ConversationHandler.END


async def cancel_signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return ConversationHandler.END
    await update.message.reply_text("Carga manual de señal cancelada.")
    return ConversationHandler.END


def manual_signal_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("exec_signal", exec_signal_command)],
        states={
            WAITING_MANUAL_SIGNAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_signal)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_signal_command)],
        allow_reentry=True,
    )


def build_bot_application() -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(manual_signal_conversation())
    for name, fn in [
        ("help", help_command),
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
    try:
        await app.bot.set_my_commands(
            [BotCommand(name, description) for name, description in BOT_COMMANDS]
        )
    except Exception:
        logger.exception("No se pudo registrar el menu de comandos en Telegram")
    await app.start()
    await app.updater.start_polling(drop_pending_updates=False)
    logger.info("Bot de comandos iniciado")
    return app
