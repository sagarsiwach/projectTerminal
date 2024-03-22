import httpx
from bs4 import BeautifulSoup
from config import read_config

# Read configuration from config.csv
config = read_config()

# Base URL for the website
base_url = "https://gotravspeed.com"

# Headers to mimic a real browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.112 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document',
    'Referer': base_url,
    'Upgrade-Insecure-Requests': '1'
}

async def login():
    async with httpx.AsyncClient() as client:
        # Step 1: Navigate to the main page
        response = await client.get(base_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to access the main page")
            exit()

        # Step 2: Submit login credentials
        login_data = {
            'name': config['username'],
            'password': config['password']
        }
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
        server_data = {
            'action': 'server',
            'value': '9'
        }
        response = await client.post(base_url + "/game/servers", data=server_data, headers=headers)
        if response.status_code != 200:
            print(f"Failed to select server")
            exit()

        # Step 5: Log in to the selected server
        server_login_data = {
            'action': 'serverLogin',
            'value[pid]': '9',
            'value[server]': '9'
        }
        response = await client.post(base_url + "/game/servers", data=server_login_data, headers=headers)
        if response.status_code != 200:
            print(f"Failed to log in to server")
            exit()

        # Step 6: Access a specific page in the game (e.g., village1.php)
        response = await client.get("https://fun.gotravspeed.com/village1.php", headers=headers)
        if response.status_code != 200:
            print(f"Failed to access the game page")
            exit()

        print(f"Successfully logged in and accessed the game page")

        cookies = client.cookies
        return cookies
