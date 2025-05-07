from discord.ext import commands
from db.mongo import sellers_col, get_tracked_asins, add_new_asin
from keepa.fetcher import fetch_seller_data, fetch_asin_details
from utils.embeds import build_listing_embed

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addseller")
    @commands.has_permissions(administrator=True)
    async def addseller(self, ctx, seller_id: str):
        channel_id = ctx.channel.id

        if sellers_col.find_one({"seller_id": seller_id}):
            await ctx.send(f"❌ Seller ID `{seller_id}` is already being tracked.")
            return

        sellers_col.insert_one({
            "seller_id": seller_id,
            "channel_id": channel_id
        })

        await ctx.send(f"✅ Seller ID `{seller_id}` has been added and will be tracked every 30 minutes.")

        # Get ASIN list from Keepa
        seller_data = await fetch_seller_data(seller_id)
        if not seller_data or "asinList" not in seller_data:
            await ctx.send(f"⚠️ Failed to fetch listings for seller `{seller_id}` right now.")
            return

        asins = seller_data["asinList"][:5]
        for asin in asins:
            asin_data = await fetch_asin_details(asin)
            if asin_data:
                embed = build_listing_embed(asin_data)
                await ctx.send(embed=embed)
                add_new_asin(asin, seller_id)

    @addseller.error
    async def addseller_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You do not have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Usage: `!addseller <seller_id>`")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
