from pymongo import MongoClient

# MongoDB setup
client = MongoClient("mongodb+srv://saniyamohammad1008:bubc9OEowXf4C09w@cluster0.dtwyxma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["genfin_db"]
collection = db["users"]

# Insert test user (you can rename or change values)
test_user = {
    "user_id": "USR101",
    "phone_number": "+919849707289",  # Your test number
    "name": "Aditi Sharma",
    "age": 38,
    "income_monthly": 50000,
    "expenses_monthly": 20000,
    "loan_status": "None",
    "credit_score": 720,
    "reminder_preferences": "Monthly",
    "balance": 35000,
    "investment_interest": "Crypto",
    "previous_queries": [
        "What is my balance?",
        "Suggest good investment options."
    ],
    "telegram_id": "N/A",
    "bank_accounts": [
        {
            "bank_name": "ICICI Bank",
            "account_type": "Savings",
            "account_number": "XXXX1010",
            "balance": 35000
        }
    ]
}

collection.insert_one(test_user)
print("✅ Test user inserted successfully!")
