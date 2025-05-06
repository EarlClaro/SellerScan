from discord.ext import commands

class UserCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="helpme")
    async def help_command(self, ctx):
        await ctx.send("👋 This bot helps you track new listings from Amazon sellers. Contact an admin to subscribe.")

def setup(bot):
    bot.add_cog(UserCommands(bot))
