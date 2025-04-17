from pymongo import MongoClient

# Your connection string
mongo_url = "mongodb+srv://saniyamohammad1008:bubc9OEowXf4C09w@cluster0.dtwyxma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongo_url)
db = client["genfin_db"]
users = db["users"]

# 🔁 Update with your actual chat ID
your_chat_id = "2038144063"  # Replace with the Telegram ID you got

result = users.update_one(
    {"user_id": "USR001"},
    {"$set": {"telegram_id": your_chat_id}}
)

if result.modified_count > 0:
    print("✅ Telegram ID updated successfully!")
else:
    print("⚠️ User not found or already updated.")
