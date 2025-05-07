import asyncio
from keepa.fetcher import fetch_asin_details
from db.mongo import get_tracked_asins, add_new_asin, sellers_col, users_col
from utils.embeds import build_listing_embed

from keepa.fetcher import fetch_seller_data, fetch_asin_details

async def check_new_listings(bot, interval=1800):
    await bot.wait_until_ready()

    while not bot.is_closed():
        for seller in sellers_col.find():
            seller_id = seller["seller_id"]
            discord_channel_id = seller["channel_id"]

            seller_data = await fetch_seller_data(seller_id)
            if not seller_data or "asinList" not in seller_data:
                continue

            tracked_asins = get_tracked_asins(seller_id)
            new_asins = [asin for asin in seller_data["asinList"] if asin not in tracked_asins]

            if new_asins:
                channel = bot.get_channel(discord_channel_id)
                for asin in new_asins[:5]:
                    asin_data = await fetch_asin_details(asin)
                    if asin_data:
                        embed = build_listing_embed(asin_data)
                        await channel.send(embed=embed)
                        add_new_asin(asin, seller_id)

        await asyncio.sleep(interval)
