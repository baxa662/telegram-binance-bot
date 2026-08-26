from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from config import settings
from models import Signal


def _conn():
    conn = sqlite3.connect(settings.database_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    with _conn() as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS processed_messages (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(chat_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_min REAL NOT NULL,
                entry_max REAL NOT NULL,
                take_profits TEXT NOT NULL,
                stop_loss REAL NOT NULL,
                leverage INTEGER NOT NULL,
                margin_type TEXT NOT NULL,
                raw_text TEXT,
                status TEXT NOT NULL DEFAULT 'NEW',
                created_at TEXT NOT NULL,
                UNIQUE(chat_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                mode TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                status TEXT NOT NULL,
                entry_min REAL NOT NULL,
                entry_max REAL NOT NULL,
                entry_price REAL,
                quantity REAL,
                initial_quantity REAL,
                stop_loss REAL NOT NULL,
                current_stop_loss REAL,
                take_profits TEXT NOT NULL,
                leverage INTEGER NOT NULL,
                risk_percent REAL,
                risk_amount REAL,
                notional REAL,
                margin_required REAL,
                entry_order_id INTEGER,
                stop_order_id INTEGER,
                tp_order_ids TEXT,
                tp_filled TEXT NOT NULL DEFAULT '[]',
                realized_pnl REAL DEFAULT 0,
                opened_at TEXT,
                closed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        if get_state("paused", None, conn=conn) is None:
            set_state("paused", "1" if settings.bot_paused else "0", conn=conn)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_state(key: str, default=None, conn=None):
    owns = conn is None
    conn = conn or _conn()
    try:
        row = conn.execute("SELECT value FROM app_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        if owns:
            conn.close()


def set_state(key: str, value: str, conn=None):
    owns = conn is None
    conn = conn or _conn()
    try:
        conn.execute(
            "INSERT INTO app_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        if owns:
            conn.commit()
    finally:
        if owns:
            conn.close()


def is_paused() -> bool:
    return get_state("paused", "0") == "1"


def set_paused(value: bool):
    set_state("paused", "1" if value else "0")


def is_message_processed(chat_id: int, message_id: int) -> bool:
    with _conn() as conn:
        return conn.execute(
            "SELECT 1 FROM processed_messages WHERE chat_id=? AND message_id=?",
            (chat_id, message_id),
        ).fetchone() is not None


def mark_message_processed(chat_id: int, message_id: int):
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO processed_messages(chat_id,message_id,created_at) VALUES(?,?,?)",
            (chat_id, message_id, _now()),
        )


def save_signal(chat_id: int, message_id: int, signal: Signal, raw_text: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO signals(
                chat_id,message_id,symbol,direction,entry_min,entry_max,take_profits,
                stop_loss,leverage,margin_type,raw_text,status,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                chat_id,
                message_id,
                signal.symbol,
                signal.direction,
                signal.entry_min,
                signal.entry_max,
                json.dumps(signal.take_profits),
                signal.stop_loss,
                signal.leverage,
                signal.margin_type,
                raw_text,
                "NEW",
                _now(),
            ),
        )
        if cur.lastrowid:
            return int(cur.lastrowid)
        row = conn.execute("SELECT id FROM signals WHERE chat_id=? AND message_id=?", (chat_id, message_id)).fetchone()
        return int(row["id"])


def signal_from_row(row: sqlite3.Row | dict) -> Signal:
    return Signal(
        symbol=row["symbol"],
        direction=row["direction"],
        entry_min=float(row["entry_min"]),
        entry_max=float(row["entry_max"]),
        take_profits=json.loads(row["take_profits"]),
        stop_loss=float(row["stop_loss"]),
        leverage=int(row["leverage"]),
        margin_type=row["margin_type"],
    )


def get_last_signal():
    with _conn() as conn:
        row = conn.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None


def get_recent_signals(limit: int = 5):
    with _conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]


def create_pending_trade(signal_id: int, signal: Signal) -> int:
    now = _now()
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO trades(
                signal_id,mode,symbol,direction,status,entry_min,entry_max,stop_loss,current_stop_loss,
                take_profits,leverage,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                signal_id,
                settings.trading_mode,
                signal.symbol,
                signal.direction,
                "PENDING_ENTRY",
                signal.entry_min,
                signal.entry_max,
                signal.stop_loss,
                signal.stop_loss,
                json.dumps(signal.take_profits),
                min(signal.leverage, settings.max_leverage),
                now,
                now,
            ),
        )
        return int(cur.lastrowid)


def list_trades(statuses: list[str] | None = None, limit: int = 50):
    with _conn() as conn:
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            rows = conn.execute(
                f"SELECT * FROM trades WHERE status IN ({placeholders}) ORDER BY id DESC LIMIT ?",
                (*statuses, limit),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def count_active_trades() -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM trades WHERE status IN ('PENDING_ENTRY','OPEN')"
        ).fetchone()
        return int(row["c"])


def active_trade_for_symbol(symbol: str):
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM trades WHERE symbol=? AND status IN ('PENDING_ENTRY','OPEN') ORDER BY id DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        return dict(row) if row else None


def get_trade(trade_id: int):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
        return dict(row) if row else None


def update_trade(trade_id: int, **fields):
    if not fields:
        return
    fields["updated_at"] = _now()
    columns = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [trade_id]
    with _conn() as conn:
        conn.execute(f"UPDATE trades SET {columns} WHERE id=?", values)


def close_trade(trade_id: int, status: str = "CLOSED", realized_pnl: float | None = None):
    fields = {"status": status, "closed_at": _now()}
    if realized_pnl is not None:
        fields["realized_pnl"] = realized_pnl
    update_trade(trade_id, **fields)
