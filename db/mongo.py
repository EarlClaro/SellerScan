from pymongo import MongoClient
from dotenv import load_dotenv
import os
import bcrypt

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["sellerscan"]

users_col = db["users"]
asins_col = db["asins"]
sellers_col = db["sellers"]

sellers_col.create_index([("seller_id", 1), ("user_id", 1)], unique=True)

# ------------------------------
# User-related operations with password hashing
# ------------------------------

def create_user(discord_id, username, password, channel_id):
    if users_col.find_one({"username": username}):
        return False  # Username already exists
    
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    users_col.insert_one({
        "discord_id": str(discord_id),
        "username": username,
        "password_hash": password_hash,
        "channel_id": channel_id,
        "seller_ids": [],
        "keepa_api_key": None  # Initialize Keepa API key as None
    })
    return True

def verify_user(username, password):
    user = users_col.find_one({"username": username})
    if user and bcrypt.checkpw(password.encode('utf-8'), user["password_hash"]):
        return user  # Login successful
    return None

def get_user_by_discord_id(discord_id):
    return users_col.find_one({"discord_id": str(discord_id)})

def update_keepa_api_key(discord_id, keepa_api_key):
    users_col.update_one({"discord_id": discord_id}, {"$set": {"keepa_api_key": keepa_api_key}})


# ------------------------------
# ASIN tracking (unchanged)
# ------------------------------

def get_tracked_asins(seller_id, user_id):
    return set(doc["asin"] for doc in asins_col.find({"seller_id": seller_id, "user_id": user_id}))

def add_new_asin(asin, seller_id, user_id):
    asins_col.update_one(
        {"asin": asin, "seller_id": seller_id, "user_id": user_id},
        {"$setOnInsert": {"asin": asin, "seller_id": seller_id, "user_id": user_id}},
        upsert=True
    )

