import asyncio
import logging

from database import init_database
from telegram_reader import start_telegram
from bot_commands import start_bot_commands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    logger.info(
        "Crypto Signal Bot iniciado"
    )

    init_database()

    bot_application = await start_bot_commands()

    try:
        await start_telegram()

    finally:
        logger.info(
            "Cerrando bot de comandos..."
        )

        await bot_application.updater.stop()
        await bot_application.stop()
        await bot_application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())