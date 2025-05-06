import discord

def build_listing_embed(asin, price, image_url):
    embed = discord.Embed(
        title="🆕 New Listing Found!",
        description=f"**ASIN:** `{asin}`\n**Price:** {price}\n[View on Amazon](https://www.amazon.com/dp/{asin})",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=image_url)
    embed.set_footer(text="First seen now")

    return embed
