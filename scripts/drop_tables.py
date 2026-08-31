#!/usr/bin/env python3

import argparse
import sqlite3
import sys

TABLES = [
    "app_state",
    "processed_messages",
    "trades",
    "signals",
]


def drop_tables(db_path: str):
    conn = sqlite3.connect(db_path)

    try:
        cursor = conn.cursor()

        for table in TABLES:
            print(f"Dropping table: {table}")
            cursor.execute(f'DROP TABLE IF EXISTS "{table}"')

        conn.commit()
        print("\nTodas las tablas fueron eliminadas correctamente.")

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Elimina tablas de la base de datos SQLite."
    )
    parser.add_argument(
        "database",
        help="Ruta al archivo SQLite, por ejemplo: bot.db"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Ejecutar sin pedir confirmación."
    )

    args = parser.parse_args()

    if not args.yes:
        print("Se eliminarán permanentemente estas tablas:")
        for table in TABLES:
            print(f"  - {table}")

        answer = input("\n¿Continuar? [y/N]: ").strip().lower()

        if answer not in ("y", "yes", "s", "si", "sí"):
            print("Operación cancelada.")
            return

    drop_tables(args.database)


if __name__ == "__main__":
    main()