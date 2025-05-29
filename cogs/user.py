from discord.ext import commands
from db.mongo import create_user, verify_user, update_keepa_api_key
from db.mongo import sellers_col, add_new_asin, users_col, asins_col
from keepa.fetcher import fetch_seller_data
from utils.time import keepa_minutes_to_utc
from datetime import datetime
from zoneinfo import ZoneInfo
from keepa.fetcher import get_token_status

# In-memory session storage
sessions = {}

# Domain map for dynamic URL generation
DOMAIN_MAP = {
    1: "com",
    2: "co.uk",
    3: "de",
    4: "fr",
    5: "co.jp",
    6: "ca",
    8: "it",
    9: "es",
    10: "in",
    11: "com.mx"
}

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="helpme")
    async def help_command(self, ctx):
        help_text = (
            "**🛠️ SellerScan Bot Commands:**\n"
            "\n"
            "`!register <username> <password> <repeat_password>` - Register a new user.\n"
            "`!login <username> <password>` - Log in to your account.\n"
            "`!logout` - Log out from the bot.\n"
            "`!setkeepaapi <api_key>` - Set or update your Keepa API key.\n"
            "`!setdomain <id>` - Set your Amazon domain (e.g., 1 for .com, 3 for .de).\n"
            "`!adduserseller <seller_id>` - Add a seller to your tracking list.\n"
            "`!removeseller <seller_id>` - Remove a seller and its related ASINs.\n"
            "`!mysellers` - List all seller IDs you're tracking.\n"
            "`!mytokens` - View your Keepa token status.\n"
            "`!helpme` - Display this help message."
        )
        await ctx.send(help_text)

    @commands.command(name="register")
    async def register(self, ctx, username: str, password: str, repeat_password: str):
        if password != repeat_password:
            await ctx.send("❌ Passwords do not match. Please try again.")
            return

        if not create_user(ctx.author.id, username, password, ctx.channel.id):
            await ctx.send("❌ Username already exists. Please choose another.")
            return

        await ctx.send(f"✅ User `{username}` has been registered successfully. Please login with !login <username> <password>")

    @commands.command(name="login")
    async def login(self, ctx, username: str, password: str):
        user = verify_user(username, password)
        if user:
            discord_id = str(ctx.author.id)
            sessions[discord_id] = username
            await ctx.send(f"✅ Login successful! Welcome, {username}. Please set your Keepa API key with !setkeepaapi <your_api_key>.")

            if not user.get("keepa_api_key"):
                await ctx.send("❌ You haven't set your Keepa API key yet. Please use !setkeepaapi <your_api_key>.")
            else:
                await ctx.send("✅ You already have a Keepa API key set. You can now add sellers.")

            domain_id = user.get("domain_id", 1)
            await ctx.send(f"🌐 Your current Amazon domain is `{domain_id}`. Use `!setdomain <id>` to change it.")
        else:
            await ctx.send("❌ Invalid username or password. Please try again.")

    @commands.command(name="setkeepaapi")
    async def setkeepaapi(self, ctx, keepa_api_key: str):
        discord_id = str(ctx.author.id)

        if discord_id not in sessions:
            await ctx.send("❌ You need to register and login first.")
            return

        update_keepa_api_key(discord_id, keepa_api_key)
        await ctx.send("✅ Your Keepa API key has been set successfully. You can now add sellers using !adduserseller <seller_id>.")

    @commands.command(name="setdomain")
    async def setdomain(self, ctx, domain_id: int):
        valid_domains = {
            1: "com", 2: "co.uk", 3: "de", 4: "fr", 5: "co.jp",
            6: "ca", 8: "it", 9: "es", 10: "in", 11: "com.mx"
        }

        if domain_id not in valid_domains:
            await ctx.send("❌ Invalid domain ID. Please choose from:\n" +
                           "\n".join([f"{k}: {v}" for k, v in valid_domains.items()]))
            return

        users_col.update_one(
            {"discord_id": str(ctx.author.id)},
            {"$set": {"domain_id": domain_id}}
        )
        await ctx.send(f"✅ Domain set to `{valid_domains[domain_id]}` (ID: {domain_id}).")

    @commands.command(name="adduserseller")
    async def addseller(self, ctx, seller_id: str):
        channel = ctx.channel
        channel_id = channel.id
        discord_id = str(ctx.author.id)

        await ctx.send(f"🔍 Fetching seller `{seller_id}` data... Please wait and don't input another command until this is done.")

        if discord_id not in sessions:
            await ctx.send("❌ You need to be logged in. Use `!login <username> <password>`.")
            return

        user = users_col.find_one({"discord_id": discord_id})
        if not user:
            await ctx.send("❌ User not found. Please register and login again.")
            return

        domain_id = user.get("domain_id", 1)

        try:
            seller_data = await fetch_seller_data(seller_id, domain_id=domain_id)
        except Exception as e:
            await ctx.send(f"❌ Error fetching data from Keepa: {str(e)}")
            return

        if not seller_data or not seller_data.get("asinList"):
            await ctx.send(f"⚠️ Seller `{seller_id}` has no current ASIN listings or data is unavailable.")
            return

        # Save seller to DB
        sellers_col.update_one(
            {"seller_id": seller_id, "channel_id": channel_id, "user_id": discord_id},
            {"$setOnInsert": {
                "seller_id": seller_id,
                "channel_id": channel_id,
                "user_id": discord_id,
                "seller_name": name
            }},
            upsert=True
        )

        asin_list = seller_data["asinList"]
        asin_last_seen = seller_data.get("asinListLastSeen", [])
        name = seller_data.get("sellerName", "N/A")

        for asin in asin_list:
            add_new_asin(asin, seller_id, discord_id)

        await ctx.send(f"✅ Seller `{seller_id}` has been added and tracked for you.")

        # Show 3 newest listings in a single message
        domain_suffix = DOMAIN_MAP.get(domain_id, "com")
        message_lines = []

        for i, asin in enumerate(asin_list[:3]):
            amazon_url = f"https://www.amazon.{domain_suffix}/dp/{asin}"
            try:
                keepa_time = asin_last_seen[i]
                timestamp = keepa_minutes_to_utc(keepa_time).astimezone(ZoneInfo("Asia/Manila")).strftime("%Y-%m-%d %I:%M:%S %p PHT")
            except Exception:
                timestamp = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Manila")).strftime("%Y-%m-%d %I:%M:%S %p PHT")

            message_lines.append(
                f"🆕 **ASIN `{asin}` from `{name}, {seller_id}`**\n"
                f"🔗 {amazon_url}\n"
                f"🕒 Listed on: `{timestamp}`\n"
            )

        await channel.send("\n".join(message_lines))


    @commands.command(name="logout")
    async def logout(self, ctx):
        discord_id = str(ctx.author.id)
        if discord_id in sessions:
            del sessions[discord_id]
            await ctx.send("✅ You have been logged out.")
        else:
            await ctx.send("❌ You are not currently logged in.")

    @commands.command(name="mytokens")
    async def mytokens(self, ctx):
        discord_id = str(ctx.author.id)
        if discord_id not in sessions:
            await ctx.send("❌ You need to be logged in to check token status.")
            return
    
        user = users_col.find_one({"discord_id": discord_id})
        if not user or not user.get("keepa_api_key"):
            await ctx.send("❌ No Keepa API key found for your account.")
            return
    
        # Temporarily override the global key with the user's key
        from keepa import fetcher
        fetcher.KEEPA_API_KEY = user["keepa_api_key"]
    
        token_data = await get_token_status(user["keepa_api_key"])
        if token_data:
            tokens = token_data["tokensLeft"]
            refill_in = round(token_data["refillIn"] / 60, 2)
            await ctx.send(f"🔑 **Keepa API Token Status:**\n🔹 Tokens left: `{tokens}`\n🔄 Refill in: `{refill_in} minutes`")
        else:
            await ctx.send("⚠️ Failed to retrieve token info. Please check your Keepa API key.")
        
    @commands.command(name="mysellers")
    async def mysellers(self, ctx):
        discord_id = str(ctx.author.id)
    
        if discord_id not in sessions:
            await ctx.send("❌ You need to be logged in to view your tracked sellers.")
            return
    
        user_sellers = list(sellers_col.find({"user_id": discord_id}))
    
        if not user_sellers:
            await ctx.send("📭 You are not tracking any sellers yet. Use `!adduserseller <seller_id>` to start.")
            return
    
        message_lines = ["📋 **Your Tracked Sellers:**"]
        for seller in user_sellers:
            seller_id = seller["seller_id"]
            seller_name = seller.get("seller_name", "N/A")
            message_lines.append(f"🔹 `{seller_id}` — **{seller_name}**")

    
        await ctx.send("\n".join(message_lines))


    @commands.command(name="removeseller")
    async def removeseller(self, ctx, seller_id: str):
        discord_id = str(ctx.author.id)

        user = users_col.find_one({'discord_id': discord_id})
        if not user:
            await ctx.send("❌ User not found. Please register first.")
            return

        # Check in sellers_col directly instead of user['seller_ids']
        seller_entry = sellers_col.find_one({'user_id': discord_id, 'seller_id': seller_id})
        if not seller_entry:
            await ctx.send(f"⚠️ Seller ID `{seller_id}` is not in your tracked list.")
            return

        sellers_col.delete_many({'user_id': discord_id, 'seller_id': seller_id})
        asins_col.delete_many({'user_id': discord_id, 'seller_id': seller_id})

        await ctx.send(f"✅ Seller `{seller_id}` and all related ASINs have been removed.")


async def setup(bot):
    await bot.add_cog(UserCommands(bot))
