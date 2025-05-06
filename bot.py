import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Load command groups
initial_extensions = ["cogs.admin", "cogs.user"]

for ext in initial_extensions:
    bot.load_extension(ext)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

bot.run(TOKEN)
