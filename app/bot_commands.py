import os
import logging

from risk_manager import calculate_trade_plan
from binance_client import get_usdt_balance
from telegram import Update
from binance_client import (
    get_futures_balance,
    get_open_positions,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from database import (
    get_last_signal,
    get_recent_signals,
)

from binance_client import (
    get_futures_balance,
    get_open_positions,
    get_usdt_balance,
    normalize_order_values,
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["TELEGRAM_ADMIN_CHAT_ID"])

TRADING_MODE = os.getenv(
    "TRADING_MODE",
    "MONITOR"
)


def is_admin(update: Update) -> bool:
    if update.effective_chat is None:
        logger.warning("No effective_chat recibido")
        return False

    logger.info(
        "Comando recibido desde chat_id=%s | admin_configurado=%s",
        update.effective_chat.id,
        ADMIN_CHAT_ID
    )

    return update.effective_chat.id == ADMIN_CHAT_ID


async def deny_if_not_admin(update: Update) -> bool:
    if is_admin(update):
        return False

    if update.message:
        await update.message.reply_text(
            "No autorizado."
        )

    return True


async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if await deny_if_not_admin(update):
        return

    message = (
        "Estado del bot\n\n"
        "Telegram Reader: activo\n"
        "Parser: activo\n"
        "Base de datos: activa\n"
        f"Trading mode: {TRADING_MODE}\n\n"
        "Binance: conectado en modo lectura"
    )

    await update.message.reply_text(message)


async def lastsignal_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if await deny_if_not_admin(update):
        return

    signal = get_last_signal()

    if signal is None:
        await update.message.reply_text(
            "No hay señales guardadas."
        )
        return

    message = (
        "Ultima señal\n\n"
        f"Par: {signal['symbol']}\n"
        f"Dirección: {signal['direction']}\n"
        f"Entrada: {signal['entry_min']} - {signal['entry_max']}\n"
        f"TPs: {signal['take_profits']}\n"
        f"SL: {signal['stop_loss']}\n"
        f"Apalancamiento: x{signal['leverage']}\n"
        f"Margen: {signal['margin_type']}\n"
        f"Message ID: {signal['message_id']}"
    )

    await update.message.reply_text(message)


async def signals_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if await deny_if_not_admin(update):
        return

    signals = get_recent_signals(limit=5)

    if not signals:
        await update.message.reply_text(
            "No hay señales guardadas."
        )
        return

    lines = [
        "Ultimas señales",
        ""
    ]

    for signal in signals:
        lines.append(
            f"{signal['symbol']} | "
            f"{signal['direction']} | "
            f"x{signal['leverage']} | "
            f"SL {signal['stop_loss']}"
        )

    await update.message.reply_text(
        "\n".join(lines)
    )


def build_bot_application():
    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "status",
            status_command
        )
    )

    application.add_handler(
        CommandHandler(
            "lastsignal",
            lastsignal_command
        )
    )

    application.add_handler(
        CommandHandler(
            "signals",
            signals_command
        )
    )

    application.add_handler(
        CommandHandler(
            "balance",
            balance_command
        )
    )

    application.add_handler(
        CommandHandler(
            "positions",
            positions_command
        )
    )

    application.add_handler(
        CommandHandler(
            "simulate",
            simulate_command
        )
    )

    return application


async def start_bot_commands():
    logger.info(
        "Iniciando bot de comandos..."
    )

    application = build_bot_application()

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    logger.info(
        "Bot de comandos iniciado."
    )

    return application

async def balance_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if await deny_if_not_admin(update):
        return

    try:
        balances = get_futures_balance()

        if not balances:
            await update.message.reply_text(
                "No hay balances disponibles."
            )
            return

        lines = [
            "Balance Futures",
            ""
        ]

        for item in balances:
            lines.append(
                f"{item['asset']}: "
                f"{item['balance']:.8f} "
                f"(disponible: {item['available']:.8f})"
            )

        await update.message.reply_text(
            "\n".join(lines)
        )

    except Exception as exc:
        logger.exception(
            "Error consultando balance de Binance"
        )

        await update.message.reply_text(
            f"Error consultando Binance: {exc}"
        )


async def positions_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if await deny_if_not_admin(update):
        return

    try:
        positions = get_open_positions()

        if not positions:
            await update.message.reply_text(
                "No hay posiciones abiertas."
            )
            return

        lines = [
            "Posiciones abiertas",
            ""
        ]

        for position in positions:
            direction = (
                "LONG"
                if position["position_amount"] > 0
                else "SHORT"
            )

            lines.extend([
                f"{position['symbol']} | {direction}",
                f"Cantidad: {position['position_amount']}",
                f"Entrada: {position['entry_price']}",
                f"Mark: {position['mark_price']}",
                f"PnL: {position['unrealized_profit']:.4f}",
                f"Leverage: x{position['leverage']}",
                f"Margin: {position['margin_type']}",
                ""
            ])

        await update.message.reply_text(
            "\n".join(lines)
        )

    except Exception as exc:
        logger.exception(
            "Error consultando posiciones"
        )

        await update.message.reply_text(
            f"Error consultando Binance: {exc}"
        )

async def simulate_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if await deny_if_not_admin(update):
        return

    signal = get_last_signal()

    if signal is None:
        await update.message.reply_text(
            "No hay señales guardadas."
        )
        return

    signal_data = {
        "symbol": signal["symbol"],
        "direction": signal["direction"],
        "entry_min": signal["entry_min"],
        "entry_max": signal["entry_max"],
        "take_profits": [
            float(x)
            for x in signal["take_profits"].split(",")
        ],
        "stop_loss": signal["stop_loss"],
        "leverage": signal["leverage"],
    }

    balance = get_usdt_balance()

    if balance["available"] <= 0:
        await update.message.reply_text(
            "No hay USDT disponibles en Futures."
        )
        return

    try:
        plan = calculate_trade_plan(
            signal=signal_data,
            account_balance=balance["available"],
            risk_percent=1.0,
        )

        normalized = normalize_order_values(
            symbol=plan["symbol"],
            quantity=plan["quantity"],
            entry_price=plan["entry_price"],
            stop_loss=plan["stop_loss"],
            take_profits=plan["take_profits"],
        )
    except Exception as exc:
        await update.message.reply_text(
            f"Error calculando operacion: {exc}"
        )
        return

    message = (
        "SIMULACION DE OPERACION\n\n"
        f"Par: {plan['symbol']}\n"
        f"Direccion: {plan['direction']}\n"
        f"Leverage: x{plan['leverage']}\n\n"

        "CALCULO ORIGINAL\n"
        f"Entrada: {plan['entry_price']:.8f}\n"
        f"Cantidad: {plan['quantity']:.8f}\n"
        f"SL: {plan['stop_loss']}\n"
        f"TPs: {plan['take_profits']}\n\n"

        "AJUSTADO A BINANCE\n"
        f"Entrada: {normalized['entry_price']}\n"
        f"Cantidad: {normalized['quantity']}\n"
        f"SL: {normalized['stop_loss']}\n"
        f"TPs: {normalized['take_profits']}\n\n"

        f"Balance disponible: "
        f"{balance['available']:.2f} USDT\n"

        f"Riesgo: "
        f"{plan['risk_percent']:.2f}%\n"

        f"Riesgo monetario: "
        f"{plan['risk_amount']:.2f} USDT\n"

        f"Notional ajustado: "
        f"{normalized['notional']:.2f} USDT\n"

        f"Margen estimado: "
        f"{normalized['notional'] / plan['leverage']:.2f} USDT\n\n"

        "REGLAS BINANCE\n"
        f"Tick size: {normalized['rules']['tick_size']}\n"
        f"Step size: {normalized['rules']['step_size']}\n"
        f"Min qty: {normalized['rules']['min_qty']}\n"
        f"Min notional: {normalized['rules']['min_notional']}\n\n"

        "NO SE ENVIO NINGUNA ORDEN."
    )

    await update.message.reply_text(message)