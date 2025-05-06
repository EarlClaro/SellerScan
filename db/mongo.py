from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["sellerscan_db"]

users_col = db["users"]
sellers_col = db["sellers"]
asins_col = db["asins"]
