from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
import os
import time
import requests
import re
import logging
import concurrent.futures
from selenium.common.exceptions import TimeoutException
from concurrent.futures import ThreadPoolExecutor
import random
import json
import math

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

session = requests.Session()

# Configuration
username = "scar"
password = "satkabir"
uid = 9  # User ID for attacking and training troops
excluded_village_ids = []
production_loops = 1
storage_loops = 1
total_production_done = 0
total_storage_done = 0
server_user = "ANDANA"  # or "M16"
global_village_number = 3  # Used for renaming the secondary villages

# Setup Firefox options
options = Options()
options.headless = True

# Function to initialize WebDriver


# Function to initialize WebDriver
def initialize_driver():
    global driver
    firefox_profile = webdriver.FirefoxProfile()
    # firefox_profile.set_preference('permissions.default.image', 2)
    options.profile = firefox_profile
    driver = webdriver.Firefox(options=options)
    logging.info("WebDriver initialized")


# Function to check internet connection


def check_internet_connection():
    while True:
        try:
            requests.get("https://www.google.com", timeout=5)
            logging.info("Internet connection is available")
            return True
        except requests.ConnectionError:
            logging.warning("No internet connection. Retrying...")
            time.sleep(1)


# Function to check host availability


def check_host():
    while True:
        try:
            response = requests.get("https://www.gotravspeed.com", timeout=5)
            if response.status_code == 200:
                logging.info("Host is available")
                return True
        except requests.RequestException:
            logging.warning("Host error. Retrying...")
            time.sleep(1)


# Function to accept cookies


def accept_cookies():
    try:
        WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "cookie__btn"))
        ).click()
        logging.info("Cookies accepted")
    except Exception as e:
        logging.error(f"Error accepting cookies: {e}")


def login():
    while True:
        try:
            driver.get("https://www.gotravspeed.com")
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "name"))
            ).send_keys(username)
            driver.find_element(By.ID, "password").send_keys(password)
            driver.find_element(By.ID, "password").send_keys(Keys.RETURN)
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//h2/font[contains(text(),'Fun')]/ancestor::div[1]")
                )
            ).click()
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@class,'default__button-o-login')]")
                )
            ).click()
            return
        except Exception as e:
            print("Error during login:", e)
            check_internet_connection()
            check_host()


def navigate_to_construction_page():
    try:
        # Navigate to the construction page with the correct URL format
        driver.get(f"https://fun.gotravspeed.com/village2.php?=BuildMode=1")
        logging.info("Navigated to construction page and enabled build mode")
    except Exception as e:
        logging.error(f"Error navigating to construction page: {e}")


def build_building(position_id, building_id, building_name):
    try:
        logging.info(
            f"Attempting to build {building_name} (ID: {building_id}) at position {position_id}"
        )
        # Extract cookies from Selenium and set them in the requests session
        selenium_cookies = driver.get_cookies()
        for cookie in selenium_cookies:
            session.cookies.set(cookie["name"], cookie["value"])
        # Send a GET request to the specific position URL to retrieve the CSRF token
        position_response = session.get(
            f"https://fun.gotravspeed.com/build.php?id={position_id}"
        )
        position_soup = BeautifulSoup(position_response.text, "html.parser")
        build_link = position_soup.find("a", class_="build")
        if build_link is None:
            logging.error("Build link not found in the response")
            # logging.error(f"Response text: {position_response.text}")
            return  # Exit the function if the build link is not found
        href = build_link["href"]
        csrf_token = href.split("&k=")[-1]
        logging.info(f"Retrieved CSRF token: {csrf_token}")
        # Send a GET request to construct the building
        build_url = f"https://fun.gotravspeed.com/village2.php?id={position_id}&b={building_id}&k={csrf_token}"
        build_response = session.get(build_url)
        if build_response.status_code == 200:
            logging.info(
                f"Successfully built {building_name} (ID: {building_id}) at position {position_id}"
            )
        else:
            logging.error(
                f"Failed to build {building_name} (ID: {building_id}) at position {position_id}"
            )
            logging.error(f"Response text: {build_response.text}")
    except Exception as e:
        logging.error(
            f"Error building {building_name} (ID: {building_id}) at position {position_id}: {e}"
        )


def build_and_upgrade(position_id, building_id, loop, building_name):
    try:
        # Build the building if it doesn't exist
        build_building(position_id, building_id, building_name)
        # Upgrade the building to the target level
        for _ in range(loop):
            is_fully_upgraded = upgrade_building(position_id, building_name)
            if is_fully_upgraded:
                break  # Exit the loop if the building is fully upgraded
    except Exception as e:
        logging.error(
            f"Error encountered during build and upgrade for {building_name}: {e}"
        )


def upgrade_building(position_id, building_name):
    try:
        # Extract cookies from Selenium and set them in the requests session
        selenium_cookies = driver.get_cookies()
        for cookie in selenium_cookies:
            session.cookies.set(cookie["name"], cookie["value"])
        # Send a GET request to the specific position URL to retrieve the CSRF token and check if the building is fully upgraded
        position_response = session.get(
            f"https://fun.gotravspeed.com/build.php?id={position_id}"
        )
        position_soup = BeautifulSoup(position_response.text, "html.parser")
        csrf_token = position_soup.find("a", {"class": "build"})["href"].split("&k=")[1]
        build_div = position_soup.find("div", {"id": "build"})
        if f"Fully" in build_div.text:
            logging.info(f"{building_name} is fully upgraded.")
            return True  # Return True if the building is fully upgraded
        # Send a GET request to upgrade the building
        upgrade_response = session.get(
            f"https://fun.gotravspeed.com/village2.php?id={position_id}&k={csrf_token}"
        )
        if upgrade_response.status_code == 200:
            logging.info(
                f"Successfully upgraded {building_name} at position {position_id}"
            )
        else:
            logging.error(
                f"Failed to upgrade {building_name} at position {position_id}. Status code: {upgrade_response.status_code}"
            )
        return False  # Return False if the building is not fully upgraded or if there was an error
    except Exception as e:
        logging.error(f"Error upgrading {building_name} at position {position_id}: {e}")
        return False  # Return False in case of an error





def build_capital_village():
    build_and_upgrade(
        position_id=26, building_id=15, loop=20, building_name="Main Building"
    )
    # build_or_upgrade_resource(position_id=1, loop=10)
    # build_or_upgrade_resource(position_id=2, loop=10)
    # build_or_upgrade_resource(position_id=3, loop=10)
    # build_or_upgrade_resource(position_id=4, loop=10)
    # build_or_upgrade_resource(position_id=5, loop=10)
    # build_or_upgrade_resource(position_id=6, loop=10)
    # build_or_upgrade_resource(position_id=7, loop=10)
    # build_or_upgrade_resource(position_id=8, loop=10)
    # build_or_upgrade_resource(position_id=9, loop=10)
    # build_or_upgrade_resource(position_id=10, loop=10)
    # build_or_upgrade_resource(position_id=11, loop=10)
    # build_or_upgrade_resource(position_id=12, loop=10)
    # build_or_upgrade_resource(position_id=13, loop=10)
    # build_or_upgrade_resource(position_id=14, loop=10)
    # build_or_upgrade_resource(position_id=15, loop=10)
    # build_or_upgrade_resource(position_id=16, loop=10)
    # build_or_upgrade_resource(position_id=17, loop=10)
    # build_or_upgrade_resource(position_id=18, loop=10)
    build_and_upgrade(
        position_id=39, building_id=16, loop=20, building_name="Rally Point"
    )
    build_and_upgrade(
        position_id=40, building_id=33, loop=20, building_name="City Wall"
    )
    build_and_upgrade(position_id=25, building_id=19, loop=20, building_name="Barracks")
    build_and_upgrade(position_id=33, building_id=22, loop=20, building_name="Academy")
    build_and_upgrade(
        position_id=30, building_id=25, loop=20, building_name="Residence"
    )
    build_and_upgrade(position_id=29, building_id=13, loop=20, building_name="Armory")
    build_and_upgrade(position_id=21, building_id=12, loop=20, building_name="Smithy")
    build_and_upgrade(
        position_id=34, building_id=7, loop=10, building_name="Iron Foundry"
    )
    build_and_upgrade(position_id=31, building_id=5, loop=10, building_name="Sawmill")
    build_and_upgrade(
        position_id=27, building_id=6, loop=10, building_name="Brickworks"
    )
    build_and_upgrade(
        position_id=24, building_id=37, loop=20, building_name="Hero's Mansion"
    )
    build_and_upgrade(
        position_id=23, building_id=44, loop=1, building_name="Christmas Tree"
    )
    build_and_upgrade(position_id=22, building_id=11, loop=20, building_name="Granary")
    build_and_upgrade(
        position_id=20, building_id=17, loop=20, building_name="Marketplace"
    )
    build_and_upgrade(position_id=19, building_id=20, loop=20, building_name="Stable")
    build_and_upgrade(
        position_id=28, building_id=21, loop=20, building_name="Siege Workshop"
    )
    build_and_upgrade(
        position_id=32, building_id=14, loop=20, building_name="Tournament Square"
    )
    build_and_upgrade(
        position_id=35, building_id=24, loop=20, building_name="Town Hall"
    )
    build_and_upgrade(position_id=38, building_id=18, loop=20, building_name="Embassy")
    build_and_upgrade(position_id=37, building_id=27, loop=20, building_name="Treasury")


# Function to handle errors during execution


def handle_error():
    try:
        continue_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Continue')]"))
        )
        continue_button.click()
    except Exception as e:
        logging.error("Error handling failed, trying to re-login:", e)
        login()


def train_settlers_concurrently():
    def send_train_request():
        response = requests.post(
            url, headers=headers, data=settlers_data, cookies=cookies
        )
        if response.status_code == 200:
            logging.info("Training Settlers in the current village")
        else:
            logging.error(f"Error during Settlers training: {response.status_code}")

    try:
        url = "https://fun.gotravspeed.com/build.php?id=30"
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
        }
        settlers_data = (
            "tf%5B10%5D=3&s1.x=50&s1.y=8"  # Set the quantity of settlers to train
        )
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(send_train_request) for _ in range(1)]
            for future in concurrent.futures.as_completed(futures):
                pass  # You can handle each future's result or exception here if needed
    except Exception as e:
        logging.error(f"Error during Settlers training in the current village: {e}")


def build_or_upgrade_resource(position_id, loop):
    try:
        for _ in range(loop):
            # Extract cookies from Selenium and set them in the requests session
            selenium_cookies = driver.get_cookies()
            for cookie in selenium_cookies:
                session.cookies.set(cookie["name"], cookie["value"])
            # Send a GET request to the specific position URL to retrieve the CSRF token
            position_response = session.get(
                f"https://fun.gotravspeed.com/build.php?id={position_id}"
            )
            position_soup = BeautifulSoup(position_response.text, "html.parser")
            csrf_token = position_soup.find("a", {"class": "build"})["href"].split(
                "&k="
            )[1]
            # Send a GET request to upgrade the building or field
            upgrade_response = session.get(
                f"https://fun.gotravspeed.com/village2.php?id={position_id}&k={csrf_token}"
            )
            if upgrade_response.status_code == 200:
                logging.info(
                    f"Successfully upgraded resource at position {position_id}"
                )
            else:
                logging.error(
                    f"Failed to upgrade resource at position {position_id}. Status code: {upgrade_response.status_code}"
                )
    except Exception as e:
        logging.error(f"Error upgrading resource at position {position_id}: {e}")


def train_settlers_and_find_new_village(capital_village_id, start_radius=11, max_radius=25):
    try:

        # Train settlers and find a new village
        train_settlers_concurrently()
        logging.info("Training 3 settlers")
        time.sleep(1)  # Add a delay to ensure settlers are trained

        # Function to generate village IDs in a spiral pattern around the capital village
        def generate_spiral_village_ids(center_id, start_radius, max_radius):
            ids = []
            for radius in range(start_radius, max_radius + 1):
                # Generate IDs in a spiral pattern
                for i in range(-radius, radius + 1):
                    ids.append(center_id - 401 * radius + i)
                for i in range(-radius + 1, radius):
                    ids.append(center_id - 401 * i + radius)
                for i in range(-radius, radius + 1):
                    ids.append(center_id + 401 * radius - i)
                for i in range(-radius + 1, radius):
                    ids.append(center_id + 401 * i - radius)
            return ids

        # Generate village IDs in a spiral pattern around the capital village
        spiral_village_ids = generate_spiral_village_ids(capital_village_id, start_radius, max_radius)
        logging.info(f"Generated spiral village IDs around capital village ID {capital_village_id}")

        # Navigate to the Map and find a suitable spot for the new village
        driver.get("https://fun.gotravspeed.com/map.php")
        logging.info("Navigated to Map")

        for village_id in spiral_village_ids:
            driver.get(f"https://fun.gotravspeed.com/village3.php?id={village_id}")
            logging.info(f"Checking village ID {village_id} for suitability")
            if "building a new village" in driver.page_source:
                logging.info(f"Found a suitable spot for a new village at ID {village_id}")
                build_new_village_link = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'building a new village')]"))
                )
                build_new_village_link.click()
                logging.info("Clicked on 'building a new village'")
                WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.ID, "btn_ok"))).click()
                logging.info("Confirmed new village")
                break  # Stop searching once a suitable spot is found

        # Wait for the new village popup and handle it
        max_attempts = 2
        attempts = 0
        while attempts < max_attempts:
            driver.refresh()  # Refresh the page to check for the popup
            try:
                continue_link = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '» continue')]"))
                )
                continue_link.click()
                logging.info("Clicked on 'Continue' in the new village popup")
                break  # Exit the loop once the popup is handled
            except TimeoutException:
                attempts += 1
                logging.info(f"Attempt {attempts}/{max_attempts} to find 'Continue' link in new village popup")

        logging.info("Finished training settlers and finding a new village")
    except Exception as e:
        logging.error(f"Error during training settlers and finding a new village: {e}")

# Function to switch to the 0000 village


def switch_to_0000_village():
    try:
        driver.get("https://fun.gotravspeed.com/village1.php?vid=5231")
        logging.info("Switched to the 0000 village")
    except Exception as e:
        logging.error(f"Error switching to the 0000 village: {e}")


def rename_village(village_id, village_name):
    # Navigate to the profile page
    driver.get(f"https://fun.gotravspeed.com/profile.php?vid={village_id}")
    # Go to the Profile tab
    profile_tab_link = WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(@href, 'profile.php?t=1')]")
        )
    )
    profile_tab_link.click()
    # Wait for the village name input to be clickable
    village_name_input = WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable((By.NAME, "dname"))
    )
    # Clear the input and type the new village name
    village_name_input.clear()
    village_name_input.send_keys(village_name)
    # Click the "ok" button to save the changes
    ok_button = WebDriverWait(driver, 3).until(
        EC.element_to_be_clickable((By.ID, "btn_ok"))
    )
    ok_button.click()


def get_village_ids(excluded_ids):
    driver.get("https://fun.gotravspeed.com/village2.php")
    village_links = WebDriverWait(driver, 3).until(
        EC.presence_of_all_elements_located(
            (
                By.XPATH,
                "//table[@id='vlist']//td[@class='link']//a[contains(@href, 'vid=')]",
            )
        )
    )
    village_ids = [link.get_attribute("href").split("=")[-1] for link in village_links]
    filtered_village_ids = [vid for vid in village_ids if vid not in excluded_ids]
    # Log the list of village IDs
    logging.info(f"Obtained village IDs: {filtered_village_ids}")
    return filtered_village_ids


def switch_to_village(village_id):
    try:
        driver.get(f"https://fun.gotravspeed.com/village2.php?vid={village_id}")
        logging.info(f"Switched to the village with ID {village_id}")
    except Exception as e:
        logging.error(f"Error switching to the village with ID {village_id}: {e}")


# ==============================================
# ==============================================
# ==============================================

def start_celebration(times):
    town_hall_id = 35  # Adjust this to the correct ID for your Town Hall
    for _ in range(times):
        try:
            switch_to_village(8426)
            # Navigate to the Town Hall
            driver.get(f"https://fun.gotravspeed.com/build.php?id={town_hall_id}")
            logging.info("Navigated to Town Hall")

            # Start the Large Celebration
            large_celebration_link = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'a=2')]"))
            )
            large_celebration_link.click()
            logging.info("Started Large Celebration")

            # Wait for the celebration to be acknowledged before starting the next one
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//p[contains(text(), 'Updated Town Hall Fully')]"))
            )

        except Exception as e:
            logging.error(f"Error during celebration: {e}")
            # Handle the error appropriately (e.g., re-login, retry, etc.)



def master_function():
    global global_village_number
    max_villages = 500  # Set the maximum number of villages you want
    # Build the capital village
    # build_capital_village()
    # Navigate to the capital village and start celebrations
    # switch_to_village(10829)  # Replace capital_village_id with the actual ID
    # for _ in range(1):
    #     start_celebration(3000)
    # train_settlers_and_find_new_village(8426)  # Pass the driver object here
    while True:
        # Get the list of current village IDs
        current_village_ids = get_village_ids(excluded_village_ids)
        newest_village_id = current_village_ids[-1]
        switch_to_village(newest_village_id)
        rename_village(newest_village_id, f"{global_village_number:04}")
        global_village_number += 1
        # Build the secondary village
        build_secondary_village()
        # Find and settle a new village
        train_settlers_and_find_new_village(9625)  # Pass the driver object here
        # start_celebration(100)  # Uncomment and replace with your function to start celebration
        # If the number of villages reaches the limit, break the loop
        if len(current_village_ids) >= max_villages:
            break


# ==============================================
# ==============================================
# ==============================================


def build_secondary_village():
    # rename_village()
    build_and_upgrade(
        position_id=26, building_id=15, loop=10, building_name="Main Building"
    )
    build_and_upgrade(
        position_id=39, building_id=16, loop=10, building_name="Rally Point"
    )
    # build_and_upgrade(position_id=40, building_id=33, loop=20, building_name="City Wall")
    # build_and_upgrade(position_id=25, building_id=19, loop=20, building_name="Barracks")
    # build_and_upgrade(position_id=33, building_id=22, loop=20, building_name="Academy")
    build_and_upgrade(
        position_id=30, building_id=25, loop=20, building_name="Residence"
    )
    # build_and_upgrade(position_id=34, building_id=7, loop=10, building_name="Iron Foundry")
    # build_and_upgrade(position_id=31, building_id=5, loop=10, building_name="Sawmill")
    # build_and_upgrade(position_id=27, building_id=6, loop=10, building_name="Brickworks")
    # build_and_upgrade(position_id=24, building_id=37, loop=20, building_name="Hero's Mansion")
    build_and_upgrade(
        position_id=24, building_id=44, loop=1, building_name="Christmas Tree"
    )
    # build_and_upgrade(position_id=37, building_id=27, loop=20, building_name="Treasury")z


def build_ww():

    build_and_upgrade(
        position_id=25, building_id=40, loop=1000, building_name="World Wonder"
    )



def rename_all_villages():
    global global_village_number
    excluded_ids = []  # Add any village IDs you want to exclude from renaming
    # Fetch the list of all current village IDs, excluding any specified
    village_ids = get_village_ids(excluded_ids)
    # It's assumed get_village_ids() returns a list of dictionaries with 'id' and 'name' keys
    # If it only returns a list of IDs, adjust the sorting and access accordingly
    # Sort villages by their IDs (assuming numeric IDs for simplicity)
    village_ids_sorted = sorted(village_ids, key=lambda x: int(x["id"]))
    for index, village in enumerate(village_ids_sorted, start=1):
        village_id = village["id"]
        # Generate a new name for the village using its index
        new_village_name = f"{index:04}"
        # Switch to the village by its ID
        switch_to_village(village_id)
        # Rename the village
        rename_village(village_id, new_village_name)
        print(f"Renamed village ID {village_id} to {new_village_name}")


# Main flow
initialize_driver()
# check_internet_connection()
check_host()
accept_cookies()
login()

while True:
    try:
        # rename_all_villages()
        master_function()
        # build_ww()
        # rename_village(10829, "0000")
        # get_village_ids(excluded_village_ids)
        # build_and_upgrade(position_id=39, building_id=16)
        # build_capital_village()
        # build_secondary_village()
        # start_celebration(10000)
        # train_settlers_and_find_new_village()
    except Exception as e:
        logging.error(
            f"Error encountered: {e}. Reinitializing driver and checking connections before retrying."
        )
        driver.quit()
        initialize_driver()
        check_internet_connection()
        check_host()
        login()
