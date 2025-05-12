import asyncio
from datetime import datetime
from keepa.fetcher import fetch_seller_data
from db.mongo import get_tracked_asins, add_new_asin, sellers_col, users_col  
from utils.embeds import build_listing_embed  # Optional if using rich embeds
from utils.time import keepa_minutes_to_utc

from db.mongo import users_col  # Add this import

async def check_new_listings(bot, interval=3600):
    await bot.wait_until_ready()

    while not bot.is_closed():
        for seller in sellers_col.find():
            seller_id = seller["seller_id"]
            discord_channel_id = seller["channel_id"]
            user_id = seller["user_id"]  # NEW

            seller_data = await fetch_seller_data(seller_id)
            if not seller_data or "asinList" not in seller_data or "asinListLastSeen" not in seller_data:
                continue

            name = seller_data.get("sellerName", "N/A")
            asin_list = seller_data["asinList"]
            asin_last_seen = seller_data["asinListLastSeen"]

            channel = bot.get_channel(discord_channel_id)
            if channel is None:
                print(f"⚠️ Channel not found for seller {seller_id}")
                continue

            tracked_asins = get_tracked_asins(seller_id, user_id)
            new_asins = [asin for asin in asin_list if asin not in tracked_asins]

            if new_asins:
                for asin in new_asins[:3]:
                    add_new_asin(asin, seller_id, user_id)
                    amazon_url = f"https://www.amazon.com/dp/{asin}"

                    try:
                        index = asin_list.index(asin)
                        keepa_time = asin_last_seen[index]
                        listed_on = keepa_minutes_to_utc(keepa_time).strftime("%Y-%m-%d %H:%M:%S UTC")
                    except Exception:
                        listed_on = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

                    await channel.send(
                        f"🆕 **New ASIN from `{seller_id} {name}`**\n"
                        f"**ASIN:** `{asin}`\n"
                        f"🔗 {amazon_url}\n"
                        f"🕒 Listed on: `{listed_on}`\n"
                        f"👤 Tracked by: <@{user_id}>"
                    )
            else:
                await channel.send(f"❌ No new listed products in the past hour for seller `{seller_id}` (`{name}`). 10 tokens consumed.")
        await asyncio.sleep(interval)
