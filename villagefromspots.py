import httpx
from bs4 import BeautifulSoup
from config import read_config, write_config
from login import login
import logging
import json
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration and potential village IDs
config = read_config()
potential_village_ids = json.load(open('potential_villages.json'))

# Extract global variables from configuration
MAX_VILLAGES = config["global"]["maxVillages"]
residence_id = config["villages"]["residenceID"]
settler_id = config["villages"]["settlerID"]

async def rename_latest_village(cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        latest_village = config["villages"]["villages"][-1]
        village_id = latest_village["villageID"]
        expected_name = latest_village["villageName"]

        # Navigate to the latest village
        await client.get(f"https://fun.gotravspeed.com/village2.php?vid={village_id}")

        # Navigate to the profile settings page
        await client.get("https://fun.gotravspeed.com/profile.php?t=1")

        # Prepare the form data for renaming the village
        form_data = {
            'e': '1',
            'oldavatar': '',
            'jahr': '',
            'monat': '0',
            'tag': '',
            'be1': '',
            'mw': '0',
            'ort': '',
            'dname': expected_name,
            'be2': '',
            's1.x': '26',
            's1.y': '16'
        }

        # Send the POST request to rename the village
        rename_response = await client.post("https://fun.gotravspeed.com/profile.php", data=form_data)
        if rename_response.status_code == 200:
            logging.info(f"Renamed latest village to {expected_name}")
        else:
            logging.error(f"Failed to rename latest village to {expected_name}")

async def get_village_ids_and_update_json(cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get("https://fun.gotravspeed.com/profile.php")
        soup = BeautifulSoup(response.text, 'html.parser')
        village_rows = soup.find('table', id='villages').find_all('tr')[1:]  # Skip the header row
        print(f"Number of village rows: {len(village_rows)}")  # Debugging

        village_data = []
        village_count = 0  # Counter for the number of villages processed
        for row in village_rows:
            cells = row.find_all('td')
            village_link = cells[0].find('a')
            if village_link:
                village_id = village_link['href'].split('=')[-1]
                village_name = village_link.text.strip()
                village_type = "secondary"
                if village_count == 0:
                    village_type = "capital"
                elif 1 <= village_count <= 10:
                    village_type = "artefact"

                village_data.append({
                    "id": village_count,
                    "villageID": int(village_id),
                    "villageName": village_name,
                    "villageType": village_type
                })
                village_count += 1  # Increment the counter

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
    async with httpx.AsyncClient(cookies=cookies) as client:
        for village_id in potential_village_ids:
            response = await client.get(f"https://fun.gotravspeed.com/village3.php?id={village_id}")
            if '»building a new village' in response.text:
                return village_id
    return None

async def send_settlers_and_handle_popup(cookies, new_village_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        # Fetch the v2v.php page to extract the key
        response = await client.get(f"https://fun.gotravspeed.com/v2v.php?id={new_village_id}")
        key = extract_key_from_v2v_page(response.text)

        # Send settlers to the new village
        response = await client.post("https://fun.gotravspeed.com/v2v.php", data={
            'id': new_village_id,
            'c': 4,
            't[1]': 0, 't[2]': 0, 't[3]': 0, 't[4]': 0, 't[5]': 0,
            't[6]': 0, 't[7]': 0, 't[8]': 0, 't[9]': 0, 't[10]': 3,
            'key': key
        })
        if response.status_code == 200:
            logging.info(f"Settlers sent to new village at {new_village_id}")
            # Update settlements.json to mark the village as settled
            settlements = load_settlements()
            settlements.append({'id': new_village_id, 'settled': True})
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
            if village_type == "capital":
                await construct_capital(cookies, latest_village["villageID"], config["buildings"]["capital"])
            elif village_type == "artefact":
                await construct_artefact(cookies, latest_village["villageID"], config["buildings"]["artefact"])
            else:
                await construct_secondary(cookies, latest_village["villageID"], config["buildings"]["secondary"])

            await train_settlers(cookies, latest_village["villageID"], residence_id, settler_id)
            await expand_village(cookies)
        except httpx.ReadTimeout:
            logging.warning(f"ReadTimeout occurred while processing village ID {latest_village['villageID']}.")
        except httpx.ConnectTimeout:
            logging.warning(f"ConnectTimeout occurred while processing village ID {latest_village['villageID']}.")

        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
