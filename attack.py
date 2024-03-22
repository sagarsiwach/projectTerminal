import httpx
from bs4 import BeautifulSoup
import logging
import asyncio
from login import login

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


async def get_player_villages(cookies, uid, excluded_village_ids):
    async with httpx.AsyncClient(cookies=cookies, follow_redirects=True) as client:
        response = await client.get(f"https://fun.gotravspeed.com/profile.php?uid={uid}")
        logging.info(f"Final URL after redirects: {response.url}")
        soup = BeautifulSoup(response.text, 'html.parser')
        village_links = soup.select('#villages a[href*="village3.php?id="]')
        villages = []
        for link in village_links:
            village_id = link['href'].split('=')[-1]
            if village_id not in excluded_village_ids:
                village_name = link.text.strip()
                village_url = f"https://fun.gotravspeed.com/v2v.php?id={village_id}"
                villages.append((village_name, village_url))
        sorted_villages = sorted(villages, key=lambda x: x[0])
        logging.info(f"Found {len(sorted_villages)} non-capital villages for player {uid} excluding village IDs {excluded_village_ids}")
        return sorted_villages


import httpx
from bs4 import BeautifulSoup
import asyncio

async def attack_village(cookies, village_url):
    try:
        # Derive the village ID from the village URL
        village_id = village_url.split('=')[-1]

        # Define your headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.160 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://fun.gotravspeed.com",
            "Referer": village_url,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

        # GET request to retrieve the key
        async with httpx.AsyncClient(cookies=cookies) as client:
            response = await client.get(village_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            key = soup.find('input', {'name': 'key'})['value']

            # Construct the data for the POST request
            data = {
                'id': village_id,
                'c': '4',  # Attack: raid
                't[1]': '0',  # Phalanx
                't[2]': '0',  # Swordsman
                't[3]': '20.0000000000000000000000e+22',  # Pathfinder
                't[4]': '0',  # Theutates Thunder
                't[5]': '0',  # Druidrider
                't[6]': '20.0000000000000000000000e+22',  # Haeduan
                't[7]': '0',  # Battering Ram
                't[8]': '0',  # Trebuchet
                't[9]': '0',  # Chief
                't[0]': '0',  # Settler
                'key': key
            }

            # POST request to send troops
            attack_response = await client.post("https://fun.gotravspeed.com/v2v.php", headers=headers, data=data)
            if attack_response.status_code == 200:
                print(f"Attacked village with ID {village_id}")
            else:
                print(f"Error attacking village with ID {village_id}: {attack_response.status_code}")

            await asyncio.sleep(0.05)

    except Exception as e:
        print(f"Error attacking village with ID {village_id}: {e}")



async def train_troops(cookies, village_id):
    async def send_train_request(session):
        url = f"https://fun.gotravspeed.com/build.php?id={village_id}"
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded",
            "sec-ch-ua": "\"Chromium\";v=\"122\", \"Not(A:Brand\";v=\"24\", \"Google Chrome\";v=\"122\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }
        data = "tf%5B2%5D=521117636153554570000&s1.x=50&s1.y=8"

        response = await session.post(url, headers=headers, data=data)
        if response.status_code == 200:
            logging.info("Training Praetorians in the current village")
        else:
            logging.error(f"Error during Praetorians training: {response.status_code}")

    async with httpx.AsyncClient(cookies=cookies) as session:
        tasks = [send_train_request(session) for _ in range(150)]
        await asyncio.gather(*tasks)

async def main():
    cookies = await login()
    uid = 9
    excluded_village_ids = ['9631']
    villages = await get_player_villages(cookies, uid, excluded_village_ids)

    while True:
        for village in villages:
            await attack_village(cookies, village[1])
            train_tasks = [train_troops(cookies, village[1].split('=')[-1]) for _ in range(100)]
            await asyncio.gather(*train_tasks)
            await asyncio.sleep(1)  # Adjust the sleep time as needed

if __name__ == "__main__":
    asyncio.run(main())
