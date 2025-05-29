import asyncio
from datetime import datetime
from keepa.fetcher import fetch_seller_data
from db.mongo import get_tracked_asins, add_new_asin, sellers_col, users_col
from utils.time import keepa_minutes_to_utc
from zoneinfo import ZoneInfo

DOMAIN_MAP = {
    1: "com", 2: "co.uk", 3: "de", 4: "fr", 5: "co.jp",
    6: "ca", 8: "it", 9: "es", 10: "in", 11: "com.mx"
}

# Per-channel message queues
message_queues = {}
queue_locks = {}

# Maximum messages per channel per interval (Discord limit)
MAX_MESSAGES_PER_INTERVAL = 5
INTERVAL_SECONDS = 5

async def send_message_worker(channel):
    """Worker task to send messages from a channel's queue respecting rate limits."""
    queue = message_queues[channel.id]
    lock = queue_locks[channel.id]

    while True:
        # Send up to MAX_MESSAGES_PER_INTERVAL messages, then wait INTERVAL_SECONDS
        messages_to_send = []
        async with lock:
            for _ in range(min(MAX_MESSAGES_PER_INTERVAL, queue.qsize())):
                try:
                    msg = queue.get_nowait()
                    messages_to_send.append(msg)
                except asyncio.QueueEmpty:
                    break

        for content in messages_to_send:
            try:
                await channel.send(content)
            except Exception as e:
                print(f"[SEND ERROR] Failed to send message to {channel.id}: {e}")

        if messages_to_send:
            # Wait to respect rate limit
            await asyncio.sleep(INTERVAL_SECONDS)
        else:
            # No messages - wait a short moment before checking again
            await asyncio.sleep(1)

async def enqueue_message(channel, content):
    """Add a message to the channel's queue and start worker if not running."""
    if channel.id not in message_queues:
        message_queues[channel.id] = asyncio.Queue()
        queue_locks[channel.id] = asyncio.Lock()
        # Start the worker task for this channel
        asyncio.create_task(send_message_worker(channel))

    await message_queues[channel.id].put(content)

async def check_new_listings(bot, interval=3600):
    await bot.wait_until_ready()

    while not bot.is_closed():
        # Prepare a dict to batch messages per channel
        messages_per_channel = {}

        for seller in sellers_col.find():
            seller_id = seller["seller_id"]
            discord_channel_id = seller["channel_id"]
            user_id = seller["user_id"]

            user = users_col.find_one({"discord_id": user_id})
            if not user:
                print(f"⚠️ User not found for seller {seller_id}")
                continue

            keepa_api_key = user.get("keepa_api_key")
            if not keepa_api_key:
                print(f"⚠️ No Keepa API key found for user {user_id}")
                continue

            domain_id = user.get("domain_id", 1)
            domain_suffix = DOMAIN_MAP.get(domain_id, "com")

            try:
                seller_data = await fetch_seller_data(
                    seller_id,
                    domain_id=domain_id,
                    keepa_api_key=keepa_api_key
                )
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
                # Compose a batch message with all new ASINs for this seller
                lines = [f"🆕 **New ASIN(s) from `{seller_id} {name}`:**"]
                for asin in new_asins[:3]:  # Limit to 3 per seller
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

                    lines.append(
                        f"**ASIN:** `{asin}`\n"
                        f"🔗 {amazon_url}\n"
                        f"🕒 Listed on: `{listed_on}`\n"
                    )
                lines.append(f"👤 Tracked by: <@{user_id}>")

                # Append this message to the channel batch
                messages_per_channel.setdefault(discord_channel_id, []).append("\n".join(lines))
            else:
                # Here we skip to reduce message spam.
                pass

        # Enqueue the batched messages per channel for sending
        for channel_id, msgs in messages_per_channel.items():
            channel = bot.get_channel(channel_id)
            if not channel:
                continue
            for msg in msgs:
                await enqueue_message(channel, msg)

        await asyncio.sleep(interval)
