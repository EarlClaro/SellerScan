from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv("MONGODB_URI")

client = MongoClient(MONGO_URI)
db = client["sellerscan"]

users_col = db["users"]
sellers_col = db["sellers"]
asins_col = db["asins"]
