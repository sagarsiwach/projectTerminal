import csv
import logging
import time
import httpx
from bs4 import BeautifulSoup
from config import read_config
from login import login

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Disable httpx logging
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

# Read configuration from the CSV file
config = read_config()

# Asynchronous function to increase production
async def increase_production_async(loop_count, cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        for _ in range(loop_count):
            try:
                # Retrieve the key for increasing production
                get_response = await client.get("https://fun.gotravspeed.com/buy2.php?t=0")
                soup = BeautifulSoup(get_response.text, 'html.parser')
                key = soup.find('input', {'name': 'key'})['value']

                # Increase production
                data = {
                    'selected_res': 4,
                    'g-recaptcha-response': 'xxxx',
                    'xor': 100,
                    'key': key
                }
                await client.post("https://fun.gotravspeed.com/buy2.php?t=0&Shop=done", data=data)
                logger.info("Resource Increased")
            except Exception as e:
                logger.error(f"Error during production increase: {e}")

# Asynchronous function to increase storage
async def increase_storage_async(loop_count, cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        for _ in range(loop_count):
            try:
                # Retrieve the key for increasing storage
                get_response = await client.get("https://fun.gotravspeed.com/buy2.php?t=2")
                soup = BeautifulSoup(get_response.text, 'html.parser')
                key = soup.find('input', {'name': 'key'})['value']

                # Increase storage
                data = {
                    'selected_res': 4,
                    'g-recaptcha-response': 'xxxx',
                    'xor': 100,
                    'key': key
                }
                await client.post("https://fun.gotravspeed.com/buy2.php?t=2&Shop=done", data=data)
                logger.info("Storage Increased")
            except Exception as e:
                logger.error(f"Error during storage increase: {e}")

# Asynchronous function to start a large celebration multiple times
async def start_large_celebration(loop_count, cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        for _ in range(loop_count):
            try:
                # Retrieve the celebration page
                get_response = await client.get("https://fun.gotravspeed.com/build.php?id=35")
                soup = BeautifulSoup(get_response.text, 'html.parser')

                # Parse the key for the large celebration
                celebration_link = soup.find('a', {'class': 'build', 'href': True})
                if celebration_link:
                    celebration_url = celebration_link['href']
                    # Start the large celebration
                    await client.get(f"https://fun.gotravspeed.com/{celebration_url}")
                    logger.info("Large Celebration Started")
                else:
                    logger.error("Failed to parse celebration key")
            except Exception as e:
                logger.error(f"Error during large celebration: {e}")

# Write updated configuration to CSV
def write_config(config):
    with open('config.csv', mode='w', newline='') as file:
        fieldnames = ['username', 'password', 'production_loops', 'storage_loops', 'headless',
                      'production_completed', 'storage_completed', 'executions_per_second', 'executions_per_minute',
                      'executions_per_hour', 'executions_last_hour', 'current_production', 'current_storage']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(config)
