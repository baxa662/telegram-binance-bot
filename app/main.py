import asyncio
import logging

from database import init_database
from telegram_reader import start_telegram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    logger.info("Crypto Signal Bot iniciado")

    init_database()

    await start_telegram()


if __name__ == "__main__":
    asyncio.run(main())