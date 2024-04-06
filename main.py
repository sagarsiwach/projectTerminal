import asyncio
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from resource import increase_production_async, increase_storage_async, start_large_celebration
# from building import construct_capital
from config import read_config
from login import login

async def main():
    cookies = await login()
    config = read_config()

    # Increase production and storage without a loop
    # await construct_capital(cookies)
    await increase_storage_async(2500, cookies)
    await increase_production_async(50000, cookies)
    # await start_large_celebration(100000, cookies)
    # print(f"Production completed: {config['production_completed']}, Storage completed: {config['storage_completed']}")

async def scheduled_task():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(main, 'interval', minutes=15)
    scheduler.start()

if __name__ == "__main__":
    asyncio.run(scheduled_task())
