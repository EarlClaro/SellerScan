from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from the .env file
MONGO_URI = os.getenv("MONGODB_URI")

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Access the database
db = client["sellerscan"]

# Access collections (you can add more collections as needed)
users_col = db["users"]
sellers_col = db["sellers"]
asins_col = db["asins"]

print(users_col.find_one())
print("Connected to MongoDB:", db)
