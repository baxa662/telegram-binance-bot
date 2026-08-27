from __future__ import annotations

import asyncio
import logging

from bot_commands import start_bot_commands
from config import settings
from database import init_database
from telegram_reader import start_telegram_reader
from trade_engine import pending_worker, positions_worker

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Crypto Signal Bot iniciando | modo=%s", settings.trading_mode)
    if settings.is_production and not settings.live_orders_enabled:
        logger.warning("PRODUCTION seleccionado pero live trading BLOQUEADO por doble confirmacion")

    init_database()
    bot_app = await start_bot_commands()

    tasks = [
        asyncio.create_task(start_telegram_reader(), name="telegram-reader"),
        asyncio.create_task(pending_worker(), name="pending-worker"),
        asyncio.create_task(positions_worker(), name="positions-worker"),
    ]

    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            exc = task.exception()
            if exc:
                raise exc
    finally:
        for task in tasks:
            task.cancel()
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())


# import asyncio
# import logging

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(message)s"
# )

# async def main():
#     logging.info("Crypto Signal Bot iniciado")

#     while True:
#         logging.info("Bot activo...")
#         await asyncio.sleep(60)


# if __name__ == "__main__":
#     asyncio.run(main())