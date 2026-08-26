from binance_api import execution_client
from config import settings

client = execution_client()
print("Mode:", settings.trading_mode)
print("Base URL:", client.base_url)
print("Ping:", client.ping())
print("USDT balance:", client.usdt_balance())
