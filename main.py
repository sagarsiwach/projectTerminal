import asyncio
import subprocess
import sys
from resource import increase_production_async, increase_storage_async
from login import login

async def main():
    while True:
        try:
            cookies = await login()

            # Perform your tasks
            await increase_storage_async(2500, cookies)
            await increase_production_async(50000, cookies)

        except Exception as e:
            print(f"An error occurred: {e}. Restarting script.")
            subprocess.Popen([sys.executable, 'main.py'])  # Start a new instance of the script
            sys.exit(1)  # Exit the current script

if __name__ == "__main__":
    asyncio.run(main())
