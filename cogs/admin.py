from discord.ext import commands
from db.mongo import sellers_col
import datetime

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="add_seller")
    async def add_seller(self, ctx, seller_id: str, channel_id: int, refresh_minutes: int = 30):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("🚫 You must be an admin to use this command.")
            return

        seller = {
            "seller_id": seller_id,
            "channel_id": channel_id,
            "refresh_interval": refresh_minutes,
            "last_checked": datetime.datetime.utcnow()
        }

        sellers_col.update_one(
            {"seller_id": seller_id},
            {"$set": seller},
            upsert=True
        )

        await ctx.send(f"✅ Seller `{seller_id}` added with {refresh_minutes}min refresh to <#{channel_id}>.")

def setup(bot):
    bot.add_cog(AdminCommands(bot))
