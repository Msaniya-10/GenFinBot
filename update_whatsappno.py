from pymongo import MongoClient

client = MongoClient("mongodb+srv://saniyamohammad1008:bubc9OEowXf4C09w@cluster0.dtwyxma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["genfin_db"]
users = db["users"]

# Replace with your actual number, no +91, just digits
your_whatsapp_number = "9059627655"

# Update the phone number in the user record
users.update_one(
    {"user_id": "USR001"},
    {"$set": {"phone_number": your_whatsapp_number}}
)

print("✅ WhatsApp number updated!")
