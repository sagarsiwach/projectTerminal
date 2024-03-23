import httpx
import asyncio
import json
import logging
from bs4 import BeautifulSoup
from login import login

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variables
MAX_VILLAGES = 500
SETTLEMENT_FILE = "settlements.json"

# Generate spiral village IDs
def generate_spiral_village_ids(center_id, max_villages=500, max_radius=25):
    radius = 1
    ids = []
    while len(ids) < max_villages and radius <= max_radius:
        for i in range(-radius, radius + 1):
            ids.append(center_id - 401 * radius + i)
        for i in range(-radius + 1, radius):
            ids.append(center_id - 401 * i + radius)
        for i in range(-radius, radius + 1):
            ids.append(center_id + 401 * radius - i)
        for i in range(-radius + 1, radius):
            ids.append(center_id + 401 * i - radius)
        radius += 1
    return ids[:max_villages]

# Load settlements from file
def load_settlements():
    try:
        with open(SETTLEMENT_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"villages": []}

# Save settlements to file
def save_settlements(settlements):
    with open(SETTLEMENT_FILE, "w") as file:
        json.dump(settlements, file, indent=4)

# Check if a village is empty and can be settled
async def is_village_empty(cookies, village_id):
    async with httpx.AsyncClient(cookies=cookies) as client:
        response = await client.get(f"https://fun.gotravspeed.com/village3.php?id={village_id}")
        return '»building a new village' in response.text

# Find empty village spots and update the settlement file
async def find_empty_village_spots(cookies, potential_village_ids):
    settlements = load_settlements()
    settled_villages = {village["id"] for village in settlements["villages"]}
    new_settlements = []
    for village_id in potential_village_ids:
        if village_id not in settled_villages and await is_village_empty(cookies, village_id):
            new_settlements.append({"id": village_id, "settled": False})
    settlements["villages"].extend(new_settlements)
    save_settlements(settlements)
    logging.info(f"Found {len(new_settlements)} new empty village spots.")

# Main function
async def main():
    cookies = await login()  # Your login cookies here
    center_village_id = 9625  # Your center village ID here

    # Generate potential village IDs
    potential_village_ids = generate_spiral_village_ids(center_village_id, MAX_VILLAGES)

    # Find empty village spots
    await find_empty_village_spots(cookies, potential_village_ids)

    # Continue with your expansion logic here...

if __name__ == "__main__":
    asyncio.run(main())
