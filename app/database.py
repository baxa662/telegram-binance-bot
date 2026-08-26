import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "/app/data/bot.db"
)


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def init_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_messages (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, message_id)
            )
        """)

        conn.execute("""
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, message_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_message_id INTEGER,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profits TEXT NOT NULL,
                leverage INTEGER NOT NULL,
                risk_percent REAL NOT NULL,
                risk_amount REAL NOT NULL,
                notional REAL NOT NULL,
                margin_required REAL NOT NULL,
                status TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    logger.info(
        "Base de datos inicializada en %s",
        DATABASE_PATH
    )


def is_message_processed(chat_id: int, message_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT 1
            FROM processed_messages
            WHERE chat_id = ? AND message_id = ?
            LIMIT 1
            """,
            (chat_id, message_id)
        )

        return cursor.fetchone() is not None


def mark_message_processed(chat_id: int, message_id: int):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO processed_messages (
                chat_id,
                message_id
            )
            VALUES (?, ?)
            """,
            (chat_id, message_id)
        )

        conn.commit()


def save_signal(
    chat_id: int,
    message_id: int,
    signal: dict,
    raw_text: str
):
    take_profits = ",".join(
        str(value)
        for value in signal["take_profits"]
    )

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO signals (
                chat_id,
                message_id,
                symbol,
                direction,
                entry_min,
                entry_max,
                take_profits,
                stop_loss,
                leverage,
                margin_type,
                raw_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                message_id,
                signal["symbol"],
                signal["direction"],
                signal["entry_min"],
                signal["entry_max"],
                take_profits,
                signal["stop_loss"],
                signal["leverage"],
                signal["margin_type"],
                raw_text
            )
        )

        conn.commit()

def get_last_signal():
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("""
            SELECT *
            FROM signals
            ORDER BY id DESC
            LIMIT 1
        """)

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)


def get_recent_signals(limit: int = 5):
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("""
            SELECT *
            FROM signals
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()

        return [dict(row) for row in rows]

def save_paper_trade(
    signal_message_id: int,
    trade: dict
):
    take_profits = ",".join(
        str(value)
        for value in trade["take_profits"]
    )

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO paper_trades (
                signal_message_id,
                symbol,
                direction,
                entry_price,
                quantity,
                stop_loss,
                take_profits,
                leverage,
                risk_percent,
                risk_amount,
                notional,
                margin_required,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_message_id,
                trade["symbol"],
                trade["direction"],
                trade["entry_price"],
                trade["quantity"],
                trade["stop_loss"],
                take_profits,
                trade["leverage"],
                trade["risk_percent"],
                trade["risk_amount"],
                trade["notional"],
                trade["margin_required"],
                trade["status"],
            )
        )

        conn.commit()

        return cursor.lastrowid