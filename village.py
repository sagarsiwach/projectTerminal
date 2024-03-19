import httpx
from bs4 import BeautifulSoup
from config import read_config, write_config
from login import login
import logging
import json
from building import construct_capital, construct_artefact, construct_secondary
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Read configuration from config.json
config = read_config()

# Global variable for maximum number of villages needed
MAX_VILLAGES = 100  # Adjust as needed

# Function to generate spiral village IDs
def generate_spiral_village_ids(center_id, radius):
    ids = []
    for i in range(-radius, radius + 1):
        ids.append(center_id - 401 * radius + i)
    for i in range(-radius + 1, radius):
        ids.append(center_id - 401 * i + radius)
    for i in range(-radius, radius + 1):
        ids.append(center_id + 401 * radius - i)
    for i in range(-radius + 1, radius):
        ids.append(center_id + 401 * i - radius)
    return ids

async def get_village_ids_and_update_json(cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get("https://fun.gotravspeed.com/profile.php")
        soup = BeautifulSoup(response.text, 'html.parser')
        village_links = soup.find_all('a', href=lambda href: href and 'village3.php?id=' in href)
        village_data = []

        for i, village_link in enumerate(village_links, start=0):
            village_id = village_link['href'].split('=')[-1]
            village_name = f"{i:04}"
            village_type = "secondary"
            if i == 0:
                village_type = "capital"
            elif 1 <= i <= 10:
                village_type = "artefact"

            village_data.append({
                "id": i,
                "villageID": int(village_id),
                "villageName": village_name,
                "villageType": village_type
            })

        # Update the configuration with the village information
        config["villages"]["villages"] = village_data
        write_config(config)

        # Print the updated configuration
        print("Updated configuration:")
        print(json.dumps(config, indent=4))

async def construct_village(cookies, village):
    if village["villageType"] == "capital":
        await construct_capital(cookies, village["villageID"])
    elif village["villageType"] == "artefact":
        await construct_artefact(cookies, village["villageID"])
    elif village["villageType"] == "secondary":
        await construct_secondary(cookies, village["villageID"])
    logging.info(f"Construction completed in village ID {village['villageID']}")

async def train_settlers(cookies, village_id, residence_id, settler_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get(f"https://fun.gotravspeed.com/build.php?id={residence_id}")
        if response.status_code != 200:
            logging.error(f"Failed to access the residence page for village ID {village_id}")
            return

        form_data = {
            f'tf[{settler_id}]': '3',
            's1.x': '73',
            's1.y': '2'
        }
        response = await client.post(f"https://fun.gotravspeed.com/build.php?id={residence_id}", data=form_data)
        if response.status_code != 200:
            logging.error(f"Failed to train settlers in village ID {village_id}")
            return

        logging.info(f"Training settlers in village ID {village_id}")

async def find_empty_village_spot(cookies, center_id, radius, existing_villages):
    spiral_village_ids = generate_spiral_village_ids(center_id, radius)
    async with httpx.AsyncClient(cookies=cookies) as client:
        for village_id in spiral_village_ids:
            if village_id not in existing_villages:
                response = await client.get(f"https://fun.gotravspeed.com/village3.php?id={village_id}")
                if '»building a new village' in response.text:
                    await send_settlers_to_new_village(cookies, village_id)
                    return village_id
    return None

async def send_settlers_to_new_village(cookies, new_village_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        # Send settlers to the new village
        response = await client.post("https://fun.gotravspeed.com/v2v.php", data={
            'id': new_village_id,
            'c': 4,
            't[1]': 0, 't[2]': 0, 't[3]': 0, 't[4]': 0, 't[5]': 0,
            't[6]': 0, 't[7]': 0, 't[8]': 0, 't[9]': 0, 't[10]': 3,
            'key': 'your_key_here'  # You need to extract this key from the page
        })
        logging.info(f"Settlers sent to new village at {new_village_id}")

async def wait_for_new_village_popup(cookies, village_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        for _ in range(5):  # Try 5 times
            response = await client.get(f"https://fun.gotravspeed.com/village1.php?id={village_id}")
            if "New village founded!" in response.text:
                logging.info("New village popup found.")
                return True
            await asyncio.sleep(1)  # Wait for 1 second before trying again
        logging.info("New village popup not found.")
        return False

async def rename_villages(cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        for village in config["villages"]["villages"]:
            village_id = village["villageID"]
            expected_name = village["villageName"]

            response = await client.get(f"https://fun.gotravspeed.com/dorf1.php?newdid={village_id}")
            soup = BeautifulSoup(response.text, 'html.parser')
            current_name = soup.find('input', {'name': 'dname'})['value']

            if current_name != expected_name:
                form_data = {
                    'id': village_id,
                    'dname': expected_name,
                    's1.x': '1',
                    's1.y': '1'
                }
                await client.post(f"https://fun.gotravspeed.com/dorf1.php", data=form_data)
                logging.info(f"Renamed village {current_name} (ID: {village_id}) to {expected_name}")

async def main():
    cookies = await login()  # Assuming you have a login function
    await get_village_ids_and_update_json(cookies)
    await rename_villages(cookies)
    while len(config["villages"]["villages"]) < MAX_VILLAGES:
        last_village = config["villages"]["villages"][-1]
        await construct_village(cookies, last_village)
        await train_settlers(cookies, last_village["villageID"], config["villages"]["residenceID"], config["villages"]["settlerID"])
        existing_villages = [village["villageID"] for village in config["villages"]["villages"]]
        capital_village_id = config["villages"]["villages"][0]["villageID"]
        new_village_id = await find_empty_village_spot(cookies, capital_village_id, 1, existing_villages)
        if new_village_id:
            await send_settlers_to_new_village(cookies, new_village_id)
            await wait_for_new_village_popup(cookies, new_village_id)
            await get_village_ids_and_update_json(cookies)
            await rename_villages(cookies)
        else:
            logging.info("No empty village spot found. Retrying...")
            await asyncio.sleep(60)  # Wait for 1 minute before retrying

if __name__ == "__main__":
    asyncio.run(main())
