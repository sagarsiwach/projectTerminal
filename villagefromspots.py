import httpx
from bs4 import BeautifulSoup
from config import read_config, write_config
from building import construct_secondary, construct_capital, construct_artefact
from login import login
import logging
import json
import asyncio


def load_settlements():
    try:
        with open('settlements.json', 'r') as file:
            data = json.load(file)
            return [village['id'] for village in data['villages'] if not village['settled']]
    except FileNotFoundError:
        return []


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration and potential village IDs
config = read_config()

# Extract global variables from configuration
MAX_VILLAGES = config["maxVillages"]
residence_id = config["villages"]["residenceID"]
settler_id = config["villages"]["settlerID"]

async def rename_latest_village(cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        latest_village = config["villages"]["villages"][-1]
        village_id = latest_village["villageID"]
        expected_name = latest_village["villageName"]

        # Navigate to the profile settings page
        await client.get(f"https://fun.gotravspeed.com/dorf1.php?newdid={village_id}&e=1")

        # Prepare the form data for renaming the village
        form_data = {
            'name': expected_name,
            's1': 'ok'
        }

        # Send the POST request to rename the village
        rename_response = await client.post(f"https://fun.gotravspeed.com/dorf1.php?newdid={village_id}&e=1", data=form_data)
        if rename_response.status_code == 200:
            logging.info(f"Renamed village ID {village_id} to {expected_name}")
        else:
            logging.error(f"Failed to rename village ID {village_id} to {expected_name}")



async def get_village_ids_and_update_json(cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get("https://fun.gotravspeed.com/profile.php")
        soup = BeautifulSoup(response.text, 'html.parser')
        village_rows = soup.find('table', id='villages').find_all('tr')[1:]  # Skip the header row

        village_data = []
        for row in village_rows:
            cells = row.find_all('td')
            village_link = cells[0].find('a')
            if village_link:
                village_id = village_link['href'].split('=')[-1]
                village_name = village_link.text.strip()

                # Determine the village type based on the index in the list
                village_type = "secondary"
                if len(village_data) == 0:
                    village_type = "capital"
                elif 1 <= len(village_data) <= 10:
                    village_type = "artefact"

                village_data.append({
                    "id": len(village_data),
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

async def find_empty_village_spot(cookies):
    unsettled_village_ids = load_settlements()
    async with httpx.AsyncClient(cookies=cookies) as client:
        for village_id in unsettled_village_ids:
            response = await client.get(f"https://fun.gotravspeed.com/village3.php?id={village_id}")
            if '»building a new village' in response.text:
                return village_id
    return None

async def send_settlers_and_handle_popup(cookies, new_village_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        # Fetch the v2v.php page to extract the key
        response = await client.get(f"https://fun.gotravspeed.com/v2v.php?id={new_village_id}")
        soup = BeautifulSoup(response.text, 'html.parser')
        key_input = soup.find('input', {'name': 'k'})
        if key_input:
            key = key_input.get('value')
        else:
            logging.error("Failed to extract CSRF key for sending settlers.")
            return False

        # Send settlers to the new village
        response = await client.post("https://fun.gotravspeed.com/v2v.php", data={
            'id': new_village_id,
            'c': 4,
            't[1]': 0, 't[2]': 0, 't[3]': 0, 't[4]': 0, 't[5]': 0,
            't[6]': 0, 't[7]': 0, 't[8]': 0, 't[9]': 0, 't[10]': 3,
            'k': key
        })
        if response.status_code == 200:
            logging.info(f"Settlers sent to new village at {new_village_id}")
            # Update settlements.json to mark the village as settled
            settlements = load_settlements()
            for village in settlements:
                if village['id'] == new_village_id:
                    village['settled'] = True
                    break
            save_settlements(settlements)

            # Wait for 2 seconds before checking for the new village popup
            await asyncio.sleep(2)

            # Check for the new village popup and handle it
            response = await client.get(f"https://fun.gotravspeed.com/village1.php?id={new_village_id}")
            if response.status_code == 302 and response.headers.get('location') == 'shownvill.php':
                # Navigate to shownvill.php to acknowledge the new village
                await client.get("https://fun.gotravspeed.com/shownvill.php")
                logging.info("New village popup handled.")
                # Wait for 1 second before continuing
                await asyncio.sleep(1)
                # Navigate to village1.php again to ensure the popup is handled
                await client.get(f"https://fun.gotravspeed.com/village1.php?id={new_village_id}")
                return True
            elif "New village founded!" in response.text:
                logging.info("New village popup handled.")
                return True
            else:
                logging.error("Failed to handle new village popup.")
                return False
        else:
            logging.error(f"Failed to send settlers to new village at {new_village_id}")
            return False



async def expand_village(cookies):
    new_village_id = await find_empty_village_spot(cookies)
    if new_village_id:
        if await send_settlers_and_handle_popup(cookies, new_village_id):  # Updated this line
            logging.info("Settlers sent to new village and popup handled.")
        else:
            logging.error("Expansion failed at sending settlers or handling popup.")
    else:
        logging.error("Expansion failed at finding empty village spot.")


async def main():
    cookies = await login()

    while len(config["villages"]["villages"]) < MAX_VILLAGES:
        await get_village_ids_and_update_json(cookies)
        await rename_latest_village(cookies)

        latest_village = config["villages"]["villages"][-1]
        village_type = latest_village.get("villageType", "secondary")

        try:
            # Find the building configuration for the current village type
            building_config = next((item for item in config["building"] if item["type"] == village_type), None)
            if building_config is None:
                logging.error(f"Building configuration for {village_type} not found")
                continue  # Skip to the next iteration if configuration not found

            if village_type == "capital":
                await construct_capital(cookies, latest_village["villageID"], building_config)
            elif village_type == "artefact":
                await construct_artefact(cookies, latest_village["villageID"], building_config)
            else:
                await construct_secondary(cookies, latest_village["villageID"], building_config)

            await train_settlers(cookies, latest_village["villageID"], residence_id, settler_id)
            await expand_village(cookies)
        except httpx.ReadTimeout:
            logging.warning(f"ReadTimeout occurred while processing village ID {latest_village['villageID']}.")
        except httpx.ConnectTimeout:
            logging.warning(f"ConnectTimeout occurred while processing village ID {latest_village['villageID']}.")

        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
