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
config = read_config()  # Assuming you have a function to read the JSON configuration
existing_villages_count = len(config["villages"]["villages"])
print(f"Existing villages count: {existing_villages_count}")

# Global variable for maximum number of villages needed
MAX_VILLAGES = 500  # Adjust as needed

# Extract residence and settler IDs from the configuration
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


# Function to generate spiral village IDs
# Function to generate spiral village IDs with initial skip
def generate_spiral_village_ids(center_id, existing_villages_count, max_radius=25):
    radius = 1
    ids = []

    while radius <= max_radius:
        for i in range(-radius, radius + 1):
            ids.append(center_id - 401 * radius + i)
        for i in range(-radius + 1, radius):
            ids.append(center_id - 401 * i + radius)
        for i in range(-radius, radius + 1):
            ids.append(center_id + 401 * radius - i)
        for i in range(-radius + 1, radius):
            ids.append(center_id + 401 * i - radius)
        radius += 1

    # Skip the initial villages based on the existing villages count
    return ids[existing_villages_count:]



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
            return True
        else:
            logging.error(f"Failed to send settlers to new village at {new_village_id}")
            return False

async def handle_new_village_popup(cookies, village_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get(f"https://fun.gotravspeed.com/village1.php?id={village_id}")
        if response.status_code == 302 and response.headers.get('location') == 'shownvill.php':
            # Navigate to shownvill.php to acknowledge the new village
            await client.get("https://fun.gotravspeed.com/shownvill.php")
            logging.info("New village popup handled.")
            return True
        elif "New village founded!" in response.text:
            logging.info("New village popup handled.")
            return True
        else:
            logging.error("Failed to handle new village popup.")
            return False


async def expand_village(cookies, center_id, radius, existing_villages):
    new_village_id = await find_empty_village_spot(cookies, center_id, radius, existing_villages)
    if new_village_id:
        if await send_settlers_to_new_village(cookies, new_village_id):
            logging.info("Settlers sent to new village.")
            # Wait a bit and then navigate to village1.php twice
            await asyncio.sleep(1)
            async with httpx.AsyncClient(cookies=cookies) as client:
                await client.get(f"https://fun.gotravspeed.com/village1.php")
                await asyncio.sleep(1)
                await client.get(f"https://fun.gotravspeed.com/village1.php")
        else:
            logging.error("Expansion failed at sending settlers.")
    else:
        logging.error("Expansion failed at finding empty village spot.")

def extract_key_from_v2v_page(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    key_input = soup.find('input', {'name': 'key'})
    if key_input:
        return key_input.get('value')
    return None


async def main():
    cookies = await login()  # Assuming you have a login function

    while len(config["villages"]["villages"]) < MAX_VILLAGES:
        await get_village_ids_and_update_json(cookies)
        await rename_latest_village(cookies)

        latest_village = config["villages"]["villages"][-1]
        try:
            if latest_village["id"] == 0:
                await construct_capital(cookies, latest_village["villageID"])
            elif 1 <= latest_village["id"] <= 10:
                await construct_artefact(cookies, latest_village["villageID"])
            else:
                await construct_secondary(cookies, latest_village["villageID"])

            await train_settlers(cookies, latest_village["villageID"], residence_id, settler_id)

            center_id = config["villages"]["villages"][0]["villageID"]  # Assuming the first village is the capital
            radius = 1  # You can adjust this as needed
            existing_villages = [v["villageID"] for v in config["villages"]["villages"]]
            await expand_village(cookies, center_id, radius, existing_villages)
        except httpx.ReadTimeout:
            logging.warning(f"ReadTimeout occurred while processing village ID {latest_village['villageID']}. Moving on to the next village.")
        except httpx.ConnectTimeout:
            logging.warning(f"ConnectTimeout occurred while processing village ID {latest_village['villageID']}. Retrying in 1 second...")
            await asyncio.sleep(1)
            continue  # Retry the current village

        # Wait a bit before starting the next iteration
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
