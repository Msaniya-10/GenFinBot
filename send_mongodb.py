from pymongo import MongoClient

# MongoDB connection
client = MongoClient("mongodb+srv://saniyamohammad1008:bubc9OEowXf4C09w@cluster0.dtwyxma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["genfin_db"]
collection = db["users"]

# Sample user with complete structure
user_data = {
    "user_id": "USR001",
    "phone_number": "4075752667",
    "name": "Saksham Zachariah",
    "age": 56,
    "income_monthly": 56947,
    "expenses_monthly": 24504,
    "loan_status": "Closed",
    "credit_score": 642,
    "reminder_preferences": "Weekly",
    "balance": 26931,
    "investment_interest": "Stocks",
    "previous_queries": [
        "When is my next EMI due?",
        "What is my current account balance?",
        "When is my EMI due in SBI?"
    ],
    "telegram_id": "160372923",
    "bank_accounts": [
        {
            "bank_name": "Axis Bank",
            "account_type": "Savings",
            "account_number": "XXXX1401",
            "balance": 32806
        }
    ]
}

# Optional: clear previous data for testing
collection.delete_many({"user_id": "USR001"})

# Insert one user
collection.insert_one(user_data)
print("✅ Sample user inserted successfully!")
