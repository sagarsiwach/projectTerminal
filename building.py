import httpx
from bs4 import BeautifulSoup
from login import login
from config import read_config, write_config
import logging

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Read configuration from
config = read_config()

# Base URL for the game
base_url = "https://fun.gotravspeed.com"

async def build_or_upgrade_resource(cookies, position_id, loop, village_id=0):
    async with httpx.AsyncClient(cookies=cookies) as client:
        for _ in range(loop):
            # Send a GET request to the specific position URL to retrieve the CSRF token
            position_response = await client.get(f"https://fun.gotravspeed.com/build.php?id={position_id}")
            position_soup = BeautifulSoup(position_response.text, "html.parser")
            build_link = position_soup.find("a", {"class": "build"})

            if build_link is None:
                logging.warning(f"No upgrade link found for resource at position {position_id}. Skipping...")
                continue  # Skip the current iteration and continue with the next one

            csrf_token = build_link["href"].split("&k=")[1]

            # Send a GET request to upgrade the building or field
            upgrade_response = await client.get(f"https://fun.gotravspeed.com/village2.php?id={position_id}&k={csrf_token}")
            if upgrade_response.status_code == 200:
                logging.info(f"Successfully upgraded resource at position {position_id}")
            else:
                logging.error(f"Failed to upgrade resource at position {position_id}. Status code: {upgrade_response.status_code}")



async def construct_and_upgrade_building(cookies, village_id, building_id, loops):
    async with httpx.AsyncClient(cookies=cookies) as client:
        for _ in range(loops):
            # Step 1: Access the construction page for the building
            response = await client.get(f"{base_url}/build.php?id={village_id}")
            if response.status_code != 200:
                logging.error(f"Failed to access the construction page for village ID {village_id}")
                continue

            # Step 2: Parse the response to extract the CSRF token and check if the building is fully upgraded
            soup = BeautifulSoup(response.text, 'html.parser')
            build_link = soup.find('a', class_='build')
            if not build_link:
                logging.warning(f"Construction link not found for village ID {village_id}, building ID {building_id}. Skipping...")
                return  # Skip the current iteration and continue with the next one
            href = build_link['href']
            csrf_token = href.split('&k=')[-1]

            # Check if any building is fully upgraded
            upgrade_message = soup.find('p', class_='none')
            if upgrade_message:
                message_words = upgrade_message.text.split()
                if len(message_words) >= 3 and message_words[0] == "Updated" and message_words[-1] == "Fully":
                    building_name = " ".join(message_words[1:-1])  # Join all words except the first and last
                    logging.info(f"{building_name} is fully upgraded. Skipping...")
                    break

            # Step 3: Make a request to construct or upgrade the building
            construct_url = f"{base_url}/village2.php?id={village_id}&b={building_id}&k={csrf_token}"
            response = await client.get(construct_url)
            if response.status_code == 200:
                logging.info(f"Successfully constructed/upgraded building ID {building_id} in village ID {village_id}")
            else:
                logging.error(f"Failed to construct/upgrade building ID {building_id} in village ID {village_id}")

async def construct_and_upgrade_villages(cookies):
    for village_type in config["buidling"]:
        village_name = village_type["type"]
        logging.info(f"Constructing and upgrading {village_name} village...")
        for building in village_type["construction"]:
            pid = building["pid"]
            bid = building["bid"]
            loop = building["loop"]
            await construct_and_upgrade_building(cookies, village_id=pid, building_id=bid, loops=loop)
            # Add a delay here if needed

async def research_academy(cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        while True:
            response = await client.get(f"{base_url}/build.php?id=33")  # Academy building ID
            soup = BeautifulSoup(response.text, 'html.parser')
            research_links = soup.select('table.build_details .act a.build')
            if not research_links:
                logging.info("All troops in the Academy are fully researched.")
                break

            for link in research_links:
                research_url = f"{base_url}/{link['href']}"
                await client.get(research_url)
                logging.info("Researching new troop in the Academy")
                break  # Break after researching one troop to re-check the Academy page

async def upgrade_armory(cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        while True:
            response = await client.get(f"{base_url}/build.php?id=29")  # Armory building ID
            soup = BeautifulSoup(response.text, 'html.parser')
            upgrade_links = soup.select('table.build_details .act a.build')
            if not upgrade_links:
                logging.info("All troops in the Armory are fully upgraded.")
                break

            for link in upgrade_links:
                troop_info = link.find_previous('div', class_='tit').text
                troop_level = int(troop_info.split('(')[-1].split(')')[0].split(' ')[-1])
                if troop_level < 20:
                    upgrade_url = f"{base_url}/{link['href']}"
                    await client.get(upgrade_url)
                    logging.info(f"Upgrading {troop_info.split('(')[0].strip()} to level {troop_level + 1} in the Armory")
                    break  # Break after upgrading one troop to re-check the Armory page


async def upgrade_smithy(cookies):
    async with httpx.AsyncClient(cookies=cookies) as client:
        while True:
            response = await client.get(f"{base_url}/build.php?id=21")  # Smithy building ID
            soup = BeautifulSoup(response.text, 'html.parser')
            upgrade_links = soup.select('table.build_details .act a.build')
            if not upgrade_links:
                logging.info("All troops in the Smithy are fully upgraded.")
                break

            for link in upgrade_links:
                troop_info = link.find_previous('div', class_='tit').text
                troop_level = int(troop_info.split('(')[-1].split(')')[0].split(' ')[-1])
                if troop_level < 20:
                    upgrade_url = f"{base_url}/{link['href']}"
                    await client.get(upgrade_url)
                    logging.info(f"Upgrading {troop_info.split('(')[0].strip()} to level {troop_level + 1} in the Smithy")
                    break  # Break after upgrading one troop to re-check the Smithy page

async def switch_village(cookies, village_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get(f"{base_url}/village2.php?vid={village_id}")
        if response.status_code == 200:
            logging.info(f"Switched to village ID {village_id}")
        else:
            logging.error(f"Failed to switch to village ID {village_id}")

async def construct_capital(cookies):
    # await switch_village(cookies, village_id)
    capital_data = next((item for item in config["building"] if item["type"] == "capital"), None)
    if capital_data is None:
        logging.error("Capital data not found in config")
        return

    for building in capital_data["construction"]:
        pid = building["pid"]
        bid = building["bid"]
        loop = building["loop"]
        if bid <= 18:  # Resource fields
            await build_or_upgrade_resource(cookies, position_id=pid, loop=loop)
        else:  # Other buildings
            await construct_and_upgrade_building(cookies, village_id=pid, building_id=bid, loops=loop)

            if bid in [13, 12, 33]:  # Armory, Smithy, Academy
                if bid == 13:
                    await upgrade_armory(cookies)
                elif bid == 12:
                    await upgrade_smithy(cookies)
                elif bid == 33:
                    await research_academy(cookies)


async def construct_artefact(cookies, village_id):
    await switch_village(cookies, village_id)
    artefact_data = next((item for item in config["building"] if item["type"] == "artefact"), None)
    if artefact_data is None:
        logging.error("Artefact data not found in config")
        return

    for building in artefact_data["construction"]:
        pid = building["pid"]
        bid = building["bid"]
        loop = building["loop"]
        await construct_and_upgrade_building(cookies, village_id=pid, building_id=bid, loops=loop)

async def construct_secondary(cookies, village_id):
    await switch_village(cookies, village_id)
    secondary_data = next((item for item in config["building"] if item["type"] == "secondary"), None)
    if secondary_data is None:
        logging.error("Secondary data not found in config")
        return

    for building in secondary_data["construction"]:
        pid = building["pid"]
        bid = building["bid"]
        loop = building["loop"]
        await construct_and_upgrade_building(cookies, village_id=pid, building_id=bid, loops=loop)
