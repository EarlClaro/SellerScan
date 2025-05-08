from discord.ext import commands
from datetime import datetime
from db.mongo import sellers_col, add_new_asin
from keepa.fetcher import fetch_seller_data
from utils.time import keepa_minutes_to_utc

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addseller")
    @commands.has_permissions(administrator=True)
    async def addseller(self, ctx, seller_id: str):
        channel = ctx.channel
        channel_id = channel.id

        if sellers_col.find_one({"seller_id": seller_id}):
            await ctx.send(f"❌ Seller ID `{seller_id}` is already being tracked.")
            return

        sellers_col.insert_one({
            "seller_id": seller_id,
            "channel_id": channel_id
        })

        await ctx.send(f"✅ Seller ID `{seller_id}` has been added and will be tracked every 30 minutes.")

        # Get seller data from Keepa
        seller_data = await fetch_seller_data(seller_id)

        if not seller_data or not seller_data.get("asinList"):
            await ctx.send(f"⚠️ Seller `{seller_id}` has no current ASIN listings or data is unavailable.")
            return

        # Send and store the 2 most recent ASINs
        asins = seller_data["asinList"][:2]
        for asin in asins:
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


    @addseller.error
    async def addseller_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You do not have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Usage: `!addseller <seller_id>`")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
