import asyncio
import logging

from telegram_reader import start_telegram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

async def main():
    logging.info("Crypto Signal Bot iniciado")

    # await start_telegram()


if __name__ == "__main__":
    asyncio.run(main())