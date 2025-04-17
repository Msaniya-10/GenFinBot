from pymongo import MongoClient

# Connect to your MongoDB
client = MongoClient("mongodb+srv://saniyamohammad1008:bubc9OEowXf4C09w@cluster0.dtwyxma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

db = client["genfin_db"]
collection = db["users"]
for user in collection.find():
    print(user.get("user_id"))
user = collection.find_one({"user_id": "tg_001"})
print(user)
# Rename the field
collection.update_one(
    {"user_id": "tg_001"},
    {"$rename": {"past_queries": "queries"}}
)

print("✅ Field renamed successfully.")
