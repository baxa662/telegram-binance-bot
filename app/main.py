import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

async def main():
    logging.info("Crypto Signal Bot iniciado")

    while True:
        logging.info("Bot activo...")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())