from pymongo import MongoClient

# Your connection string
mongo_url = "mongodb+srv://saniyamohammad1008:bubc9OEowXf4C09w@cluster0.dtwyxma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongo_url)
db = client["genfin_db"]
users = db["users"]

# HDFC Bank Account details
new_bank_account = {
    "bank_name": "HDFC Bank",
    "account_type": "Savings",
    "account_number": "XXXX1234",  # Replace with actual account number
    "balance": 50000  # Replace with the actual balance
}

# Update the user with user_id "USR001" by adding the new bank account to the array
result = users.update_one(
    {"user_id": "USR001"},
    {"$push": {"bank_accounts": new_bank_account}}
)

if result.modified_count > 0:
    print("✅ New bank account added successfully!")
else:
    print("⚠️ User not found or account already exists.")
