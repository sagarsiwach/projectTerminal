import asyncio
from resource import increase_production_async, increase_storage_async, start_large_celebration
from config import read_config
from login import login

async def main():
    cookies = await login()
    config = read_config()

    # Loop for increasing production and storage
    while True:
        await increase_storage_async(10000, cookies)
        await increase_production_async(10000, cookies)
        # await start_large_celebration(50000, cookies)
        # print(f"Production completed: {config['production_completed']}, Storage completed: {config['storage_completed']}")

if __name__ == "__main__":
    asyncio.run(main())
