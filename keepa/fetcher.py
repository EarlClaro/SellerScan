import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
KEEPA_API_KEY = os.getenv("KEEPA_API_KEY")

async def fetch_seller_data(seller_id, domain_id=1, keepa_api_key=None):
    if not keepa_api_key:
        raise ValueError("No Keepa API key provided")

    url = f"https://api.keepa.com/seller?key={keepa_api_key}&domain={domain_id}&seller={seller_id}&storefront=1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            print("Keepa API response:", data)
            if "sellers" not in data:
                return None
            return data["sellers"].get(seller_id)

async def get_token_status(keepa_api_key):
    url = f"https://api.keepa.com/token?key={keepa_api_key}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if "tokensLeft" in data and "refillIn" in data:
                return data
            return None

