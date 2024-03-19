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
MAX_VILLAGES = 100  # Adjust as needed

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
        print(json.dumps(config, indent=4))

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
    print("Debugging config in rename_all_villages:", config)  # Add this line for debugging
    async with httpx.AsyncClient(cookies=cookies) as client:
        for village in config["villages"]["villages"]:
            village_id = village["villageID"]
            expected_name = village["villageName"]

            response = await client.get(f"https://fun.gotravspeed.com/profile.php?vid={village_id}&t=1")
            if response.status_code != 200:
                logging.error(f"Failed to access the profile page for village ID {village_id}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            dname_input = soup.find('input', {'name': 'dname'})
            if dname_input is None:
                logging.error(f"Could not find the 'dname' input element for village ID {village_id}")
                continue

            current_name = dname_input['value']
            if current_name != expected_name:
                await rename_village(village_id, expected_name, cookies)
                logging.info(f"Renamed village {current_name} (ID: {village_id}) to {expected_name}")


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
# Function to find an empty village spot
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


# Function to send settlers to a new village
# Function to send settlers to a new village
async def send_settlers_to_new_village(cookies, new_village_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.112 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://fun.gotravspeed.com',
        'Upgrade-Insecure-Requests': '1'
    }

    async with httpx.AsyncClient(cookies=cookies) as client:
        # Send settlers to the new village
        response = await client.post("https://fun.gotravspeed.com/v2v.php", data={
            'id': new_village_id,
            'c': 4,
            't[1]': 0, 't[2]': 0, 't[3]': 0, 't[4]': 0, 't[5]': 0,
            't[6]': 0, 't[7]': 0, 't[8]': 0, 't[9]': 0, 't[10]': 3,
            'key': 'your_key_here'  # You need to extract this key from the page
        }, headers=headers)

        # Keep checking for the shownvill.php page for 5 times with a delay of 1 second each
        for _ in range(5):
            if "shownvill.php" in str(response.url):
                logging.info("Handling new village popup...")
                await asyncio.sleep(1)  # Wait for 1 second
                response = await client.get("https://fun.gotravspeed.com/village1.php", headers=headers)
                break  # Exit the loop if the shownvill.php page is found

        logging.info(f"Settlers sent to new village at {new_village_id}")




async def handle_new_village_popup(cookies):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.112 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://fun.gotravspeed.com',
        'Upgrade-Insecure-Requests': '1'
    }
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get("https://fun.gotravspeed.com/village1.php", headers=headers)
        if "shownvill.php" in str(response.url):
            print("Handling new village popup...")
            await client.get("https://fun.gotravspeed.com/village1.php", headers=headers)



async def check_village_find_and_train_settlers(cookies):
    if not config["villages"]["villages"]:
        logging.error("No villages found in the configuration.")
        return

    last_village = config["villages"]["villages"][-1]

    # Ensure construction is done in the last village
    if not last_village["constructionDone"]:
        if last_village["villageType"] == "capital":
            await construct_capital(cookies, last_village["villageID"])
        elif last_village["villageType"] == "artefact":
            await construct_artefact(cookies, last_village["villageID"])
        elif last_village["villageType"] == "secondary":
            await construct_secondary(cookies, last_village["villageID"])
        last_village["constructionDone"] = True
        logging.info(f"Construction completed in village ID {last_village['villageID']}")

    # Train settlers in the last village
    await train_settlers(cookies, last_village["villageID"], config["villages"]["residenceID"], config["villages"]["settlerID"])
    logging.info(f"Trained settlers in village ID {last_village['villageID']}")

    # Find and settle the next village
    existing_villages = [village["villageID"] for village in config["villages"]["villages"]]
    center_village_id = config["villages"]["villages"][0]["villageID"]
    search_radius = 5  # Adjust as needed
    new_village_id = await find_empty_village_spot(cookies, center_village_id, search_radius, existing_villages)
    if new_village_id:
        logging.info(f"Found empty village spot at ID {new_village_id}")
        await send_settlers_to_new_village(cookies, new_village_id)
        new_village_data = {
            "id": len(config["villages"]["villages"]),
            "villageID": new_village_id,
            "villageName": f"{len(config['villages']['villages']):04}",
            "villageType": "secondary",
            "villageFind": False,
            "constructionDone": False
        }
        config["villages"]["villages"].append(new_village_data)
        write_config(config)
    else:
        logging.info("No empty village spot found within the specified radius.")



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


async def main():
    cookies = await login()  # Assuming you have a login function
    config = read_config()
    await get_village_ids_and_update_json(cookies)
    await rename_all_villages(cookies, config)
    for _ in range(MAX_VILLAGES):
        await check_village_find_and_train_settlers(cookies)
        await handle_new_village_popup(cookies)  # Check for new village popup after each iteration
        config = read_config()  # Reload the config to get the updated information


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
