import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from tasks.refresher import check_new_listings
from keep_alive import keep_alive

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Discord token not found in environment variables.")
    
intents = discord.Intents.default()
intents.message_content = True  # Make sure this is enabled
intents.dm_messages = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for cog in bot.cogs:
        print(f"Loaded cog: {cog}")

async def load_extensions():
    # Correctly await the loading of the cogs
    await bot.load_extension("cogs.admin")
    await bot.load_extension("cogs.user")  # Add the user cog

async def main():
    async with bot:
        await load_extensions()  # Ensure this is awaited
        bot.loop.create_task(check_new_listings(bot, interval=3600))  # 1 hour
        await bot.start(TOKEN)


if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())
