from discord.ext import commands

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="add_seller")
    async def add_seller(self, ctx, seller_id: str):
        # Placeholder: Save seller to MongoDB
        await ctx.send(f"📦 Seller `{seller_id}` added and being tracked.")

def setup(bot):
    bot.add_cog(AdminCommands(bot))
