import asyncio
from datetime import datetime
from keepa.fetcher import fetch_seller_data
from db.mongo import get_tracked_asins, add_new_asin, sellers_col
from utils.embeds import build_listing_embed  # Optional if using rich embeds
from utils.time import keepa_minutes_to_utc

async def check_new_listings(bot, interval=3600):  # Check every hour
    await bot.wait_until_ready()

    while not bot.is_closed():
        for seller in sellers_col.find():
            seller_id = seller["seller_id"]
            discord_channel_id = seller["channel_id"]

            # Fetch seller data
            seller_data = await fetch_seller_data(seller_id)
            if not seller_data or "asinList" not in seller_data or "asinListLastSeen" not in seller_data:
                continue

            # Extract extra info
            name = seller_data.get("sellerName", "N/A")
            last_indexed = keepa_minutes_to_utc(seller_data.get("lastListingUpdate", 0)).strftime("%Y-%m-%d %H:%M:%S UTC")
            tracked_since = seller.get("tracked_since", datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S UTC")
            last_update = seller.get("last_update", datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S UTC")

            # Get the tracked ASINs for the seller
            tracked_asins = get_tracked_asins(seller_id)
            asin_list = seller_data["asinList"]
            asin_last_seen = seller_data["asinListLastSeen"]
            name = seller_data.get("sellerName", "N/A")

            new_asins = [asin for asin in asin_list if asin not in tracked_asins]

            # Get the corresponding Discord channel
            channel = bot.get_channel(discord_channel_id)
            if channel is None:
                print(f"⚠️ Channel not found for seller {seller_id}")
                continue

            # Send new ASIN data
            if new_asins:
                for asin in new_asins[:3]:
                    add_new_asin(asin, seller_id)
                    amazon_url = f"https://www.amazon.com/dp/{asin}"

                    # Get Keepa timestamp and convert to UTC
                    try:
                        index = asin_list.index(asin)
                        keepa_time = asin_last_seen[index]
                        listed_on = keepa_minutes_to_utc(keepa_time).strftime("%Y-%m-%d %H:%M:%S UTC")
                    except Exception:
                        listed_on = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

                    # Send info to channel
                    await channel.send(
                        f"🆕 **Latest ASIN from `{seller_id}`**\n"
                        f"**ASIN:** `{asin}`\n"
                        f"**Name:** `{name}`\n"
                        f"🔗 {amazon_url}\n"
                        f"🕒 Listed on: `{listed_on}`\n"
                        f"📅 Tracked Since: `{tracked_since}`\n"
                        f"📦 Last Update: `{last_update}`\n"
                        f"📈 Last Indexed by Keepa: `{last_indexed}`"
                    )
            else:
                await channel.send(f"❌ No new listed products in the past hour for seller `{seller_id}` (`{name}`). 10 tokens consumed.")

        await asyncio.sleep(interval)
