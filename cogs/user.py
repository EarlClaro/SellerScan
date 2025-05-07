from discord.ext import commands

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="helpme")
    async def help_command(self, ctx):
        print("Help command triggered!")
        await ctx.send("👋 This bot helps you track new listings from Amazon sellers. Contact an admin to subscribe.")

async def setup(bot):
    await bot.add_cog(UserCommands(bot))
