from discord.ext import commands
from datetime import datetime
from db.mongo import sellers_col, add_new_asin, get_tracked_asins, users_col, asins_col
from keepa.fetcher import fetch_seller_data
from utils.time import keepa_minutes_to_utc  # Ensure this import is correct

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addseller")
    @commands.has_permissions(administrator=True)
    async def addseller(self, ctx, seller_id: str):
        channel = ctx.channel
        channel_id = channel.id

        # Check if seller_id is already tracked
        if sellers_col.find_one({"seller_id": seller_id}):
            await ctx.send(f"❌ Seller ID `{seller_id}` is already being tracked.")
            return

        # Add the new seller to the sellers collection in MongoDB
        tracked_since = datetime.utcnow()
        sellers_col.insert_one({
            "seller_id": seller_id,
            "channel_id": channel_id,
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

        name = seller_data.get("sellerName", "N/A")

        # Send the 3 latest ASINs
        for asin in asin_list[:3]:
            amazon_url = f"https://www.amazon.com/dp/{asin}"
            try:
                index = asin_list.index(asin)
                keepa_time = asin_last_seen[index]
                timestamp = keepa_minutes_to_utc(keepa_time).strftime("%Y-%m-%d %H:%M:%S UTC")
            except Exception:
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            await channel.send(
                f"🆕 **Latest ASIN from `{seller_id} {name}`**\n"
                f"**ASIN:** `{asin}`\n"
                f"🔗 {amazon_url}\n"
                f"🕒 Listed on: `{timestamp}`\n"
            )


    @commands.command(name="cleardb")
    @commands.has_permissions(administrator=True)
    async def clear_database(self, ctx):
        # Delete all data from users, sellers, and asins collections in MongoDB
        users_col.delete_many({})
        sellers_col.delete_many({})
        asins_col.delete_many({})
        await ctx.send("🗑️ All user, seller, and ASIN data has been cleared from the database.")

    @addseller.error
    async def addseller_error(self, ctx, error):
        # Handle error if the user doesn't have permission or missing arguments
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You do not have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Usage: `!addseller <seller_id>`")

    @clear_database.error
    async def clear_database_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You do not have permission to use this command.")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
