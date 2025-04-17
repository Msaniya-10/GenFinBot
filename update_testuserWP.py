from pymongo import MongoClient

client = MongoClient("mongodb+srv://saniyamohammad1008:bubc9OEowXf4C09w@cluster0.dtwyxma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["genfin_db"]
collection = db["users"]

user_data = {
    "user_id": "USR101",
    "name": "Hafeeza",
    "phone_number": "9849707289",
    "age": 45,
    "income_monthly": 45000,
    "expenses_monthly": 22000,
    "loan_status": "None",
    "credit_score": 720,
    "reminder_preferences": "Monthly",
    "balance": 55000,
    "investment_interest": "Mutual Funds",
    "previous_queries": [],
    "telegram_id": None,
    "bank_accounts": [
        {
            "bank_name": "HDFC Bank",
            "account_type": "Savings",
            "account_number": "XXXX2001",
            "balance": 55000
        }
    ]
}

collection.insert_one(user_data)
print("✅ Mom registered successfully!")
