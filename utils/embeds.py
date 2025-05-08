import discord
from datetime import datetime, timedelta

def build_listing_embed(asin_data):
    asin = asin_data.get("asin")
    title = asin_data.get("title", "Unknown Title")
    url = f"https://www.amazon.com/dp/{asin}"
    img_url = f"https://images-na.ssl-images-amazon.com/images/I/{asin_data.get('imagesCSV', '').split(',')[0]}" if asin_data.get("imagesCSV") else None
    category = asin_data.get("categoryTree", [{}])[-1].get("name", "Unknown Category")

    # Date listed conversion from Keepa days
    listed_since_days = asin_data.get("listedSince")
    if listed_since_days:
        date_listed = datetime(2011, 1, 1) + timedelta(days=listed_since_days)
        listed_str = date_listed.strftime("%Y-%m-%d %H:%M UTC")
    else:
        listed_str = "N/A"

    embed = discord.Embed(
        title="🆕 New Listing From Seller Shop Detected!",
        url=url,
        description=f"[View on Amazon]({url})",
        color=discord.Color.green()
    )
    embed.add_field(name="Item", value=title, inline=False)
    embed.add_field(name="Category", value=category, inline=True)
    embed.add_field(name="ASIN", value=asin, inline=True)
    embed.add_field(name="Date Listed", value=listed_str, inline=False)
    if img_url:
        embed.set_thumbnail(url=img_url)

    return embed
