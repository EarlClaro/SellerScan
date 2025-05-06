import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
KEEPA_KEY = os.getenv("KEEPA_API_KEY")

BASE_URL = "https://api.keepa.com"

async def fetch_offers(seller_id):
    url = f"{BASE_URL}/query?key={KEEPA_KEY}&domain=1&seller={seller_id}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"❌ Keepa API error {resp.status}")
                return None
            data = await resp.json()
            return data.get("products", [])
