import asyncio
from resource import increase_production_async, increase_storage_async, start_large_celebration
from building import construct_capital
from config import read_config
from login import login

async def main():
    cookies = await login()
    config = read_config()

    # Increase production and storage without a loop
    await construct_capital(cookies)
    while True:
        await increase_storage_async(5000, cookies)
        await increase_production_async(12500, cookies)
        # await start_large_celebration(80000, cookies)
        # print(f"Production completed: {config['production_completed']}, Storage completed: {config['storage_completed']}")

if __name__ == "__main__":
    asyncio.run(main())
