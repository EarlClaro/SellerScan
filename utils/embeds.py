import discord

def build_listing_embed(asin_data):
    asin = asin_data.get("asin")
    title = asin_data.get("title", "Unknown Title")
    url = f"https://www.amazon.com/dp/{asin}"
    img_url = f"https://images-na.ssl-images-amazon.com/images/I/{asin_data.get('imagesCSV', '').split(',')[0]}" if asin_data.get("imagesCSV") else None
    price = round(asin_data.get("buyBoxPrice", 0) / 100, 2) if asin_data.get("buyBoxPrice") else "N/A"
    category = asin_data.get("categoryTree", [{}])[-1].get("name", "Unknown Category")
    brand = asin_data.get("brand", "Unknown Brand")
    store_name = asin_data.get("sellerId")  # May require separate seller lookup for store name
    rank = asin_data.get("salesRank", "N/A")
    monthly_sales = asin_data.get("salesPerMonth", "N/A")

    embed = discord.Embed(
        title=f"🆕 New Listing From Seller Shop Detected!",
        url=url,
        description=f"[View on Amazon]({url})",
        color=discord.Color.green()
    )
    embed.add_field(name="Item", value=title, inline=False)
    embed.add_field(name="Price", value=f"${price}", inline=True)
    embed.add_field(name="Category", value=category, inline=True)
    embed.add_field(name="ASIN", value=asin, inline=True)
    embed.add_field(name="Rank", value=rank, inline=True)
    embed.add_field(name="Monthly Sales", value=monthly_sales, inline=True)
    embed.add_field(text=f"Store ID: {store_name}")

    if img_url:
        embed.set_thumbnail(url=img_url)

    return embed
