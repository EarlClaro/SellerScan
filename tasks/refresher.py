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

            # Get the tracked ASINs for the seller
            tracked_asins = get_tracked_asins(seller_id)
            asin_list = seller_data["asinList"]
            asin_last_seen = seller_data["asinListLastSeen"]

            new_asins = [asin for asin in asin_list if asin not in tracked_asins]

            # Get the corresponding Discord channel
            channel = bot.get_channel(discord_channel_id)
            if channel is None:
                print(f"⚠️ Channel not found for seller {seller_id}")
                continue

            # Send new ASIN data
            if new_asins:
                for asin in new_asins[:2]:
                    add_new_asin(asin, seller_id)
                    amazon_url = f"https://www.amazon.com/dp/{asin}"

                    # Get Keepa timestamp and convert to UTC
                    try:
                        index = asin_list.index(asin)
                        keepa_time = asin_last_seen[index]
                        timestamp = keepa_minutes_to_utc(keepa_time).strftime("%Y-%m-%d %H:%M:%S UTC")
                    except Exception:
                        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

                    # Send information to the channel
                    await channel.send(
                        f"🆕 **Latest ASIN from `{seller_id}`**\n"
                        f"**ASIN:** `{asin}`\n"
                        f"🔗 {amazon_url}\n"
                        f"🕒 Listed on: `{timestamp}`"
                    )
            else:
                await channel.send(f"❌ No new listed products in the past hour for seller `{seller_id}`. No tokens consumed.")

        await asyncio.sleep(interval)
