from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["sellerscan"]
users_col = db["users"]
sellers_col = db["sellers"]
asins_col = db["asins"]

def get_tracked_asins(seller_id):
    return set(doc["asin"] for doc in asins_col.find({"seller_id": seller_id}))

def add_new_asin(asin, seller_id):
    asins_col.update_one(
        {"asin": asin, "seller_id": seller_id},
        {"$setOnInsert": {"asin": asin, "seller_id": seller_id}},
        upsert=True
    )

print(users_col.find_one())
print("Connected to MongoDB:", db)
