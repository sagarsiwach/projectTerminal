import httpx
from bs4 import BeautifulSoup
from config import read_config, write_config
from login import login
import logging
import json
from building import construct_capital, construct_artefact, construct_secondary

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Read configuration from config.json
config = read_config()

# Global variable for maximum number of villages needed
MAX_VILLAGES = 10  # Adjust as needed

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
                "villageType": village_type,
                "villageFind": False,
                "constructionDone": False
            })

        # Update the configuration with the village information
        config["villages"]["villages"] = village_data
        write_config(config)

        # Print the updated configuration
        print("Updated configuration:")
        # print(json.dumps(config, indent=4))

async def rename_village(village_id, new_name, cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        # Get the profile page for the village to retrieve the form data
        response = await client.get(f"https://fun.gotravspeed.com/profile.php?vid={village_id}&t=1")
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find the current village name and other form data
        current_name = soup.find('input', {'name': 'dname'})['value']
        form_data = {
            'e': '1',
            'oldavatar': soup.find('input', {'name': 'oldavatar'})['value'],
            'jahr': '',
            'monat': '0',
            'tag': '',
            'be1': '',
            'mw': '0',
            'ort': '',
            'dname': new_name,
            'be2': '',
            's1.x': '25',
            's1.y': '1'
        }
        # Send a POST request to update the village name
        await client.post(f"https://fun.gotravspeed.com/profile.php?vid={village_id}", data=form_data)

async def rename_all_villages(cookies, config):
    # Ensure the village information in the config file is up-to-date
    await get_village_ids_and_update_json(cookies)

    async with httpx.AsyncClient(cookies=cookies) as client:
        # Iterate over the villages in the updated config file
        for village in config["villages"]["villages"]:
            village_id = village["villageID"]
            expected_name = village["villageName"]

            # Get the current name of the village from the game
            response = await client.get(f"https://fun.gotravspeed.com/profile.php?vid={village_id}&t=1")
            soup = BeautifulSoup(response.text, 'html.parser')
            current_name = soup.find('input', {'name': 'dname'})['value']

            # Rename the village if its name does not match the expected format
            if current_name != expected_name:
                await rename_village(village_id, expected_name, cookies)
                logging.info(f"Renamed village {current_name} (ID: {village_id}) to {expected_name}")

async def train_settlers(cookies, village_id, residence_id, settler_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        # Access the residence page to train settlers
        response = await client.get(f"https://fun.gotravspeed.com/build.php?id={residence_id}")
        if response.status_code != 200:
            logging.error(f"Failed to access the residence page for village ID {village_id}")
            return

        # Parse the response to extract the CSRF token
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'k'})['value']

        # Train settlers
        form_data = {
            'action': 'train',
            'u': settler_id,
            'k': csrf_token,
            's1': 'ok'
        }
        await client.post(f"https://fun.gotravspeed.com/build.php?id={residence_id}", data=form_data)
        logging.info(f"Training settlers in village ID {village_id}")

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

# Function to find an empty village spot
async def find_empty_village_spot(cookies, center_id, radius, existing_villages):
    spiral_village_ids = generate_spiral_village_ids(center_id, radius)
    async with httpx.AsyncClient(cookies=cookies) as client:
        for village_id in spiral_village_ids:
            if village_id not in existing_villages:
                response = await client.get(f"https://fun.gotravspeed.com/village3.php?id={village_id}")
                if '»building a new village' in response.text:
                    return village_id
    return None

# Function to send settlers to a new village
async def send_settlers_to_new_village(cookies, village_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get(f"https://fun.gotravspeed.com/v2v.php?id={village_id}")
        soup = BeautifulSoup(response.text, 'html.parser')
        key = soup.find('input', {'name': 'key'})['value']
        data = {
            'id': village_id,
            'c': 4,
            't[1]': 0, 't[2]': 0, 't[3]': 0, 't[4]': 0, 't[5]': 0,
            't[6]': 0, 't[7]': 0, 't[8]': 0, 't[9]': 0, 't[10]': 3,
            'key': key
        }
        await client.post("https://fun.gotravspeed.com/v2v.php", data=data)
        logging.info(f"Settlers sent to new village at {village_id}")

async def check_village_find_and_train_settlers(cookies):
    existing_villages = [village["villageID"] for village in config["villages"]["villages"]]
    center_village_id = config["villages"]["villages"][0]["villageID"]
    search_radius = 5  # Adjust as needed

    # Ensure construction is completed and train settlers
    for village in config["villages"]["villages"]:
        if not village["constructionDone"]:
            # Complete construction based on village type
            if village["villageType"] == "capital":
                await construct_capital(cookies, village["villageID"])
            elif village["villageType"] == "artefact":
                await construct_artefact(cookies, village["villageID"])
            elif village["villageType"] == "secondary":
                await construct_secondary(cookies, village["villageID"])
            village["constructionDone"] = True
            write_config(config)
            logging.info(f"Construction completed in village ID {village['villageID']}")

        if not village["villageFind"]:
            # Train settlers
            await train_settlers(cookies, village["villageID"], config["villages"]["residenceID"], config["villages"]["settlerID"])
            village["villageFind"] = True  # Mark that settlers are trained and ready to find a new village
            write_config(config)
            logging.info(f"Trained settlers in village ID {village['villageID']}")

    # Find and settle a new village spot
    new_village_id = await find_empty_village_spot(cookies, center_village_id, search_radius, existing_villages)
    if new_village_id:
        logging.info(f"Found empty village spot at ID {new_village_id}")
        await send_settlers_to_new_village(cookies, new_village_id)
        # Update JSON configuration here with the new village details
    else:
        logging.info("No empty village spot found within the specified radius.")




async def main():
    cookies = await login()  # Assuming you have a login function
    config = read_config()
    await get_village_ids_and_update_json(cookies)
    await rename_all_villages(cookies, config)
    for _ in range(MAX_VILLAGES):
        await check_village_find_and_train_settlers(cookies)
        config = read_config()  # Reload the config to get the updated information

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
