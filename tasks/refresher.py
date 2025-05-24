import asyncio
from datetime import datetime
from keepa.fetcher import fetch_seller_data
from db.mongo import get_tracked_asins, add_new_asin, sellers_col, users_col
from utils.time import keepa_minutes_to_utc
from zoneinfo import ZoneInfo

# Domain map for generating correct Amazon links
DOMAIN_MAP = {
    1: "com", 2: "co.uk", 3: "de", 4: "fr", 5: "co.jp",
    6: "ca", 8: "it", 9: "es", 10: "in", 11: "com.mx"
}

# Helper function to throttle and safely send messages
async def safe_send(channel, content):
    try:
        await asyncio.sleep(1.5)  # Basic throttling between sends
        await channel.send(content)
    except Exception as e:
        print(f"[SEND ERROR] Failed to send message: {e}")

async def check_new_listings(bot, interval=3600):
    await bot.wait_until_ready()

    while not bot.is_closed():
        for seller in sellers_col.find():
            seller_id = seller["seller_id"]
            discord_channel_id = seller["channel_id"]
            user_id = seller["user_id"]

            user = users_col.find_one({"discord_id": user_id})
            if not user:
                print(f"⚠️ User not found for seller {seller_id}")
                continue

            domain_id = user.get("domain_id", 1)
            domain_suffix = DOMAIN_MAP.get(domain_id, "com")

            try:
                seller_data = await fetch_seller_data(seller_id, domain_id=domain_id)
            except Exception as e:
                print(f"❌ Error fetching data for seller {seller_id}: {str(e)}")
                continue

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
                for asin in new_asins[:3]:  # Limit to top 3 new ASINs
                    add_new_asin(asin, seller_id, user_id)
                    amazon_url = f"https://www.amazon.{domain_suffix}/dp/{asin}"

                    try:
                        index = asin_list.index(asin)
                        keepa_time = asin_last_seen[index]
                        listed_on = keepa_minutes_to_utc(keepa_time).astimezone(
                            ZoneInfo("Asia/Manila")).strftime("%Y-%m-%d %I:%M:%S %p PHT")
                    except Exception:
                        listed_on = datetime.utcnow().replace(
                            tzinfo=ZoneInfo("UTC")).astimezone(
                            ZoneInfo("Asia/Manila")).strftime("%Y-%m-%d %I:%M:%S %p PHT")

                    message = (
                        f"🆕 **New ASIN from `{seller_id} {name}`**\n"
                        f"**ASIN:** `{asin}`\n"
                        f"🔗 {amazon_url}\n"
                        f"🕒 Listed on: `{listed_on}`\n"
                        f"👤 Tracked by: <@{user_id}>"
                    )
                    await safe_send(channel, message)
            else:
                message = (
                    f"ℹ️ No new ASINs for seller `{seller_id} {name}`. 10 tokens used\n"
                    f"👤 Tracked by: <@{user_id}>"
                )
                await safe_send(channel, message)
                print(f"[INFO] No new ASINs for seller {seller_id} ({name}) — message sent.")

        await asyncio.sleep(interval)
