import json
from pymongo import MongoClient

# Load data
with open('financial_users_with_banks.json', 'r') as file:
    users = json.load(file)

# MongoDB setup
client = MongoClient("mongodb+srv://saniyamohammad1008:bubc9OEowXf4C09w@cluster0.dtwyxma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["genfin_db"]
collection = db["users"]

# Optional: Clear previous entries
# collection.delete_many({})

# Insert users
result = collection.insert_many(users)
print(f"✅ Inserted {len(result.inserted_ids)} users successfully!")
