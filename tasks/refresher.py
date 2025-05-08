import asyncio
from datetime import datetime
from keepa.fetcher import fetch_seller_data
from db.mongo import get_tracked_asins, add_new_asin, sellers_col
from utils.embeds import build_listing_embed  # Optional if using rich embeds
from utils.time import keepa_minutes_to_utc

async def check_new_listings(bot, interval=1800):
    await bot.wait_until_ready()

    while not bot.is_closed():
        for seller in sellers_col.find():
            seller_id = seller["seller_id"]
            discord_channel_id = seller["channel_id"]

            # Fetch seller data
            seller_data = await fetch_seller_data(seller_id)
            if not seller_data or "asinList" not in seller_data:
                continue

            # Get the tracked ASINs for the seller
            tracked_asins = get_tracked_asins(seller_id)
            new_asins = [asin for asin in seller_data["asinList"] if asin not in tracked_asins]

            if new_asins:
                channel = bot.get_channel(discord_channel_id)
                if channel is None:
                    print(f"⚠️ Channel not found for seller {seller_id}")
                    continue

                for asin in new_asins[:2]:
                    add_new_asin(asin, seller_id)
                    amazon_url = f"https://www.amazon.com/dp/{asin}"
                    index = seller_data["asinList"].index(asin)
                    keepa_time = seller_data["asinListLastSeen"][index]
                    timestamp = keepa_minutes_to_utc(keepa_time).strftime("%Y-%m-%d %H:%M:%S UTC")
                    await channel.send(
                        f"🆕 **New ASIN Detected!**\n"
                        f"**ASIN:** `{asin}`\n"
                        f"🔗 {amazon_url}\n"
                        f"🕒 Listed on: `{timestamp}`"
                    )

        await asyncio.sleep(interval)
