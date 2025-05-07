import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

KEEPA_API_KEY = os.getenv("KEEPA_API_KEY")
DOMAIN_ID = 1  # 1 = Amazon.com

async def fetch_seller_data(seller_id):
    url = f"https://api.keepa.com/seller?key={KEEPA_API_KEY}&domain={DOMAIN_ID}&seller={seller_id}&storefront=1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if "sellers" not in data:
                return None
            return data["sellers"].get(seller_id)

async def fetch_asin_details(asin):
    url = f"https://api.keepa.com/product?key={KEEPA_API_KEY}&domain={DOMAIN_ID}&asin={asin}&history=0"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if "products" not in data or not data["products"]:
                return None
            return data["products"][0]