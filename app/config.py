from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _csv_floats(name: str, default: str) -> List[float]:
    raw = os.getenv(name, default)
    values = [float(x.strip()) for x in raw.split(",") if x.strip()]
    if not values:
        raise ValueError(f"{name} no puede estar vacio")
    total = sum(values)
    if abs(total - 1.0) > 0.02:
        raise ValueError(f"{name} debe sumar aproximadamente 1.0; suma={total}")
    return values


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    database_path: str
    trading_mode: str
    bot_paused: bool
    enable_production_trading: bool
    production_confirmation: str

    telegram_api_id: int
    telegram_api_hash: str
    telegram_source_channel_id: int
    telegram_session_path: str
    telegram_bot_token: str
    telegram_admin_chat_id: int

    binance_api_key: str
    binance_api_secret: str
    binance_testnet_api_key: str
    binance_testnet_api_secret: str
    binance_recv_window: int
    binance_timeout_seconds: int

    risk_percent: float
    ignore_risk_percent: bool
    max_leverage: int
    max_margin_percent: float
    max_open_trades: int
    allow_multiple_positions_per_symbol: bool

    entry_strategy: str
    signal_expiry_minutes: int
    entry_range_tolerance_percent: float
    tp_allocations: List[float]

    move_sl_to_breakeven_after_tp1: bool
    move_sl_to_tp1_after_tp2: bool
    position_poll_seconds: int
    pending_entry_poll_seconds: int

    allow_manual_close: bool
    allow_manual_breakeven: bool

    @property
    def is_monitor(self) -> bool:
        return self.trading_mode == "MONITOR"

    @property
    def is_paper(self) -> bool:
        return self.trading_mode == "PAPER"

    @property
    def is_testnet(self) -> bool:
        return self.trading_mode == "TESTNET"

    @property
    def is_production(self) -> bool:
        return self.trading_mode == "PRODUCTION"

    @property
    def live_orders_enabled(self) -> bool:
        if self.is_testnet:
            return True
        if not self.is_production:
            return False
        return (
            self.enable_production_trading
            and self.production_confirmation == "I_UNDERSTAND_LIVE_TRADING"
        )


def load_settings() -> Settings:
    mode = os.getenv("TRADING_MODE", "MONITOR").strip().upper()
    if mode not in {"MONITOR", "PAPER", "TESTNET", "PRODUCTION"}:
        raise ValueError("TRADING_MODE debe ser MONITOR, PAPER, TESTNET o PRODUCTION")

    settings = Settings(
        app_env=os.getenv("APP_ENV", "production"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        database_path=os.getenv("DATABASE_PATH", "/app/data/bot.db"),
        trading_mode=mode,
        bot_paused=_bool("BOT_PAUSED", False),
        enable_production_trading=_bool("ENABLE_PRODUCTION_TRADING", False),
        production_confirmation=os.getenv("PRODUCTION_CONFIRMATION", ""),
        telegram_api_id=int(os.environ["TELEGRAM_API_ID"]),
        telegram_api_hash=os.environ["TELEGRAM_API_HASH"],
        telegram_source_channel_id=int(os.environ["TELEGRAM_SOURCE_CHANNEL_ID"]),
        telegram_session_path=os.getenv("TELEGRAM_SESSION_PATH", "/app/data/telegram"),
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_admin_chat_id=int(os.environ["TELEGRAM_ADMIN_CHAT_ID"]),
        binance_api_key=os.getenv("BINANCE_API_KEY", ""),
        binance_api_secret=os.getenv("BINANCE_API_SECRET", ""),
        binance_testnet_api_key=os.getenv("BINANCE_TESTNET_API_KEY", ""),
        binance_testnet_api_secret=os.getenv("BINANCE_TESTNET_API_SECRET", ""),
        binance_recv_window=_int("BINANCE_RECV_WINDOW", 5000),
        binance_timeout_seconds=_int("BINANCE_TIMEOUT_SECONDS", 10),
        risk_percent=_float("RISK_PERCENT", 1.0),
        ignore_risk_percent=_bool("IGNORE_RISK_PERCENT", False),
        max_leverage=_int("MAX_LEVERAGE", 15),
        max_margin_percent=_float("MAX_MARGIN_PERCENT", 25.0),
        max_open_trades=_int("MAX_OPEN_TRADES", 3),
        allow_multiple_positions_per_symbol=_bool("ALLOW_MULTIPLE_POSITIONS_PER_SYMBOL", False),
        entry_strategy=os.getenv("ENTRY_STRATEGY", "MARKET_IF_IN_RANGE").upper(),
        signal_expiry_minutes=_int("SIGNAL_EXPIRY_MINUTES", 120),
        entry_range_tolerance_percent=_float("ENTRY_RANGE_TOLERANCE_PERCENT", 0.10),
        tp_allocations=_csv_floats("TP_ALLOCATIONS", "0.33,0.33,0.34"),
        move_sl_to_breakeven_after_tp1=_bool("MOVE_SL_TO_BREAKEVEN_AFTER_TP1", True),
        move_sl_to_tp1_after_tp2=_bool("MOVE_SL_TO_TP1_AFTER_TP2", True),
        position_poll_seconds=_int("POSITION_POLL_SECONDS", 5),
        pending_entry_poll_seconds=_int("PENDING_ENTRY_POLL_SECONDS", 3),
        allow_manual_close=_bool("ALLOW_MANUAL_CLOSE", True),
        allow_manual_breakeven=_bool("ALLOW_MANUAL_BREAKEVEN", True),
    )

    if settings.risk_percent <= 0 or settings.risk_percent > 5:
        raise ValueError("RISK_PERCENT debe estar entre 0 y 5")
    if settings.max_margin_percent <= 0 or settings.max_margin_percent > 100:
        raise ValueError("MAX_MARGIN_PERCENT debe estar entre 0 y 100")
    if settings.is_production and not settings.live_orders_enabled:
        # Allowed to boot, but execution remains hard-disabled.
        pass

    return settings


settings = load_settings()
