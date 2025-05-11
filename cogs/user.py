from discord.ext import commands
from db.mongo import create_user, verify_user, get_user_by_discord_id, update_keepa_api_key
from datetime import datetime
from db.mongo import sellers_col, add_new_asin, get_tracked_asins, users_col, asins_col
from keepa.fetcher import fetch_seller_data
from utils.time import keepa_minutes_to_utc

# In-memory session storage
sessions = {}

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="helpme")
    async def help_command(self, ctx):
        await ctx.send("👋 This bot helps you track new listings from Amazon sellers. Contact an admin to subscribe.")

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
            sessions[discord_id] = username  # Save session
            await ctx.send(f"✅ Login successful! Welcome, {username}. Please set your Keepa API key with !setkeepaapi <your_api_key>.")

            if not user.get("keepa_api_key"):
                await ctx.send("❌ You haven't set your Keepa API key yet. Please use !setkeepaapi <your_api_key>.")
            else:
                await ctx.send("✅ You already have a Keepa API key set. You can now add sellers.")
        else:
            await ctx.send("❌ Invalid username or password. Please try again.")

    @commands.command(name="setkeepaapi")
    async def setkeepaapi(self, ctx, keepa_api_key: str):
        discord_id = str(ctx.author.id)

        if discord_id not in sessions:
            await ctx.send("❌ You need to register and login first.")
            return

        # Update Keepa API key in the database
        update_keepa_api_key(discord_id, keepa_api_key)
        await ctx.send("✅ Your Keepa API key has been set successfully. You can now add sellers using !adduserseller <seller_id>.")

    @commands.command(name="adduserseller")
    async def addseller(self, ctx, seller_id: str):
        channel = ctx.channel
        channel_id = channel.id

        # Check if seller_id is already tracked
        if sellers_col.find_one({"seller_id": seller_id}):
            await ctx.send(f"❌ Seller ID `{seller_id}` is already being tracked.")
            return

        # Add the new seller to the sellers collection in MongoDB
        sellers_col.insert_one({
            "seller_id": seller_id,
            "channel_id": channel_id
        })

        await ctx.send(f"✅ Seller ID `{seller_id}` has been added and will be tracked every hour.")

        # Fetch seller data from Keepa API
        seller_data = await fetch_seller_data(seller_id)

        if not seller_data or not seller_data.get("asinList"):
            await ctx.send(f"⚠️ Seller `{seller_id}` has no current ASIN listings or data is unavailable.")
            return

        asin_list = seller_data["asinList"]
        asin_last_seen = seller_data.get("asinListLastSeen", [])

        # Insert all ASINs into the database
        for asin in asin_list:
            add_new_asin(asin, seller_id)

        # Send the 2 latest ASINs
        for asin in asin_list[:2]:
            amazon_url = f"https://www.amazon.com/dp/{asin}"
            try:
                index = asin_list.index(asin)
                keepa_time = asin_last_seen[index]
                timestamp = keepa_minutes_to_utc(keepa_time).strftime("%Y-%m-%d %H:%M:%S UTC")
            except Exception:
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            await channel.send(
                f"🆕 **Latest ASIN from `{seller_id}`**\n"
                f"**ASIN:** `{asin}`\n"
                f"🔗 {amazon_url}\n"
                f"🕒 Listed on: `{timestamp}`"
            )

    @commands.command(name="logout")
    async def logout(self, ctx):
        discord_id = str(ctx.author.id)
        if discord_id in sessions:
            del sessions[discord_id]
            await ctx.send("✅ You have been logged out.")
        else:
            await ctx.send("❌ You are not currently logged in.")

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
