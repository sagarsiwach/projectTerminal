import httpx
import logging
import json
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urlencode

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Read configuration from config.json
with open('config.json', 'r') as f:
    config = json.load(f)

# Global variables
MAX_VILLAGES = 500
BASE_URL = 'https://fun.gotravspeed.com'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.112 Safari/537.36'
}

# Base URL for the website
base_url = "https://gotravspeed.com"

# Function to extract key from v2v.php page
def extract_key_from_v2v_page(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    key_input = soup.find('input', {'name': 'key'})
    if key_input:
        return key_input.get('value')
    return None

async def login():
    async with httpx.AsyncClient() as client:
        # Step 1: Navigate to the main page
        response = await client.get(base_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to access the main page")
            exit()

        # Step 2: Submit login credentials
        login_data = {"name": config["username"], "password": config["password"]}
        response = await client.post(base_url, data=login_data, headers=headers)
        if "Login failed" in response.text:
            print(f"Login failed")
            exit()
        else:
            print("Login successful")

        # Step 3: Navigate to the server selection page
        response = await client.get(base_url + "/game/servers", headers=headers)
        if response.status_code != 200:
            print(f"Failed to access the server selection page")
            exit()

        # Step 4: Select a server (server ID 9 in this example)
        server_data = {"action": "server", "value": "9"}
        response = await client.post(
            base_url + "/game/servers", data=server_data, headers=headers
        )
        if response.status_code != 200:
            print(f"Failed to select server")
            exit()


        # Step 5: Log in to the selected server
        server_login_data = {
            "action": "serverLogin",
            "value[pid]": "9",
            "value[server]": "9",
        }
        response = await client.post(
            base_url + "/game/servers", data=server_login_data, headers=headers
        )
        if response.status_code != 200:
            print(f"Failed to log in to server")
            exit()
            # Step 5.5: Check for the shownvill.php popup after logging into the server
            if "shownvill.php" in response.url:
                print("Handling new village popup...")
                await asyncio.sleep(1)  # Wait for 1 second
                response = await client.get("https://fun.gotravspeed.com/village1.php", headers=headers)
                if response.status_code != 200:
                    print("Failed to bypass new village popup")
                    exit()

        # Step 6: Access a specific page in the game (e.g., village1.php)
        response = await client.get(
            "https://fun.gotravspeed.com/village1.php", headers=headers
        )
        if response.status_code != 200:
            print(f"Failed to access the game page")
            exit()

        print(f"Successfully logged in and accessed the game page")

        cookies = client.cookies
        return cookies

async def send_settlers_to_new_village(cookies, new_village_id):
    """
    Sends settlers to a new village spot.
    """
    async with httpx.AsyncClient(cookies=cookies, headers=headers) as client:
        # Fetch the v2v.php page to extract the key
        response = await client.get(f'{BASE_URL}/v2v.php?id={new_village_id}')
        key = extract_key_from_v2v_page(response.text)

        # Send settlers to the new village
        form_data = {
            'id': str(new_village_id),
            'c': '4',
            't[1]': '0', 't[2]': '0', 't[3]': '0', 't[4]': '0', 't[5]': '0',
            't[6]': '0', 't[7]': '0', 't[8]': '0', 't[9]': '0', 't[10]': '3',
            'key': key
        }
        response = await client.post(f'{BASE_URL}/v2v.php', data=form_data)
        if response.status_code == 200:
            logging.info(f'Settlers sent to new village at {new_village_id}')
            return True
        else:
            logging.error(f'Failed to send settlers to new village at {new_village_id}')
            return False

async def train_settlers(cookies, village_id, residence_id, settler_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        # Navigate to the residence page
        residence_response = await client.get(f"https://fun.gotravspeed.com/build.php?id={residence_id}")
        if residence_response.status_code != 200:
            logging.error(f"Failed to access the residence page for village ID {village_id}")
            return

        # Check if settlers can be trained or if they are already trained
        soup = BeautifulSoup(residence_response.text, 'html.parser')
        settler_available = soup.find('span', class_='info')
        updated_residence = soup.find('p', class_='none', text='Updated Residence Fully')
        if settler_available and "Available: 0" in settler_available.text and not updated_residence:
            # Prepare the form data for training settlers
            form_data = {
                f'tf[{settler_id}]': '3',
                's1.x': '66',
                's1.y': '10'
            }
            # Send the POST request to train settlers
            training_response = await client.post(f"https://fun.gotravspeed.com/build.php?id={residence_id}", data=form_data)
            if training_response.status_code == 200:
                logging.info(f"Training settlers in village ID {village_id}")
            else:
                logging.error(f"Failed to train settlers in village ID {village_id}")
        else:
            logging.info("Settlers already trained or not available for training in village ID {village_id}")

async def handle_new_village_popup(cookies, village_id):
    """
    Handles the new village popup and acknowledges the new village.
    """
    async with httpx.AsyncClient(cookies=cookies, headers=headers) as client:
        response = await client.get(f'{BASE_URL}/village1.php?id={village_id}')
        if response.status_code == 302 and response.headers.get('location') == 'shownvill.php':
            # Navigate to shownvill.php to acknowledge the new village
            await client.get(f'{BASE_URL}/shownvill.php')
            logging.info('New village popup handled.')
            return True
        elif "New village founded!" in response.text:
            logging.info('New village popup handled.')
            return True
        else:
            logging.error('Failed to handle new village popup.')
            return False

async def find_empty_village_spot(cookies, center_id, radius, existing_villages):
    """
    Finds an empty village spot in a spiral pattern from the center village.
    """
    async with httpx.AsyncClient(cookies=cookies, headers=headers) as client:
        for village_id in generate_spiral_village_ids(center_id, radius):
            if village_id not in existing_villages:
                response = await client.get(f'{BASE_URL}/village3.php?id={village_id}')
                if '»building a new village' in response.text:
                    return village_id
    return None

def generate_spiral_village_ids(center_id, radius):
    """
    Generates village IDs in a spiral pattern from the center village.
    """
    ids = []
    for r in range(1, radius + 1):
        for x in range(-r, r + 1):
            ids.append(center_id - 401 * r + x)
        for y in range(-r + 1, r):
            ids.append(center_id - 401 * y + r)
        for x in range(-r, r + 1):
            ids.append(center_id + 401 * r - x)
        for y in range(-r + 1, r):
            ids.append(center_id + 401 * y - r)
    return ids

async def expand_village(cookies, center_id, radius, existing_villages):
    """
    Expands the village by finding an empty spot and sending settlers.
    """
    new_village_id = await find_empty_village_spot(cookies, center_id, radius, existing_villages)
    if new_village_id:
        if await send_settlers_to_new_village(cookies, new_village_id):
            logging.info('Settlers sent to new village.')
            # Wait a bit and then navigate to village1.php twice
            await asyncio.sleep(1)
            async with httpx.AsyncClient(cookies=cookies, headers=headers) as client:
                await client.get(f'{BASE_URL}/village1.php')
                await asyncio.sleep(1)
                await client.get(f'{BASE_URL}/village1.php')
            await handle_new_village_popup(cookies, new_village_id)
        else:
            logging.error('Expansion failed at sending settlers.')
    else:
        logging.error('Expansion failed at finding empty village spot.')

async def get_village_ids(cookies):
    """
    Fetches the village IDs and updates the configuration file.
    """
    async with httpx.AsyncClient(cookies=cookies, headers=headers) as client:
        response = await client.get(f'{BASE_URL}/profile.php')
        soup = BeautifulSoup(response.text, 'html.parser')
        village_rows = soup.find('table', id='villages').find_all('tr')[1:]  # Skip the header row
        logging.info(f'Number of village rows: {len(village_rows)}')

        village_data = []
        village_count = 0
        for row in village_rows:
            cells = row.find_all('td')
            village_link = cells[0].find('a')
            if village_link:
                village_id = int(village_link['href'].split('=')[-1])
                village_name = village_link.text.strip()
                village_type = "secondary"
                if village_count == 0:
                    village_type = "capital"
                elif 1 <= village_count <= 10:
                    village_type = "artefact"

                village_data.append({
                    "id": village_count,
                    "villageID": village_id,
                    "villageName": village_name,
                    "villageType": village_type
                })
                village_count += 1

        # Update the configuration with the village information
        config["villages"]["villages"] = village_data
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)

        logging.info('Updated configuration:\n%s', json.dumps(config, indent=4))


async def main():
    cookies = await login()
    if not cookies:
        return

    while len(config["villages"]["villages"]) < MAX_VILLAGES:
        await get_village_ids(cookies)

        # Rename the latest village (if needed)
        latest_village = config["villages"]["villages"][-1]
        expected_name = latest_village["villageName"]
        if expected_name != "New village":
            async with httpx.AsyncClient(cookies=cookies, headers=headers) as client:
                village_id = latest_village["villageID"]
                await client.get(f'{BASE_URL}/village2.php?vid={village_id}')
                await client.get(f'{BASE_URL}/profile.php?t=1')

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
                response = await client.post(f'{BASE_URL}/profile.php', data=form_data)
                if response.status_code == 200:
                    logging.info(f'Renamed latest village to {expected_name}')
                else:
                    logging.error(f'Failed to rename latest village to {expected_name}')

        # Construct and upgrade buildings based on village type
        if latest_village["villageType"] == "capital":
            from building import construct_capital
            await construct_capital(cookies, latest_village["villageID"])
        elif latest_village["villageType"] == "artefact":
            from building import construct_artefact
            await construct_artefact(cookies, latest_village["villageID"])
        elif latest_village["villageType"] == "secondary":
            from building import construct_secondary
            await construct_secondary(cookies, latest_village["villageID"])

        # Train settlers in the latest village
        from village import train_settlers
        residence_id = config["villages"]["residenceID"]
        settler_id = config["villages"]["settlerID"]
        await train_settlers(cookies, latest_village["villageID"], residence_id, settler_id)

        # Expand the village by finding an empty spot and sending settlers
        center_id = config["villages"]["villages"][0]["villageID"]  # Assuming the first village is the capital
        radius = 1  # You can adjust this as needed
        existing_villages = [v["villageID"] for v in config["villages"]["villages"]]
        await expand_village(cookies, center_id, radius, existing_villages)

        # Wait a bit before starting the next iteration
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
