from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from pymongo import MongoClient
import cohere
import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

# Setup clients
co = cohere.Client(COHERE_API_KEY)
client = MongoClient(MONGO_URL)
db = client["genfin_db"]
users_collection = db["users"]

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I'm GenFinBot, your AI finance assistant 💰. Ask me anything related to banking, investment, or finance!")

def get_stock_price(symbol):
    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol.upper(),
        "apikey": ALPHA_VANTAGE_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()

    try:
        quote = data["Global Quote"]
        price = quote["05. price"]
        change = quote["10. change percent"]
        return f"📈 {symbol.upper()} is currently trading at ₹{float(price):,.2f} ({change})"
    except KeyError:
        return "⚠️ Invalid stock symbol or data not available."

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.message.chat.id)
    user_query = update.message.text.lower()
    user = users_collection.find_one({"telegram_id": telegram_id})

    if not user:
        await update.message.reply_text("❗You are not a registered user in the system.")
        return

    # Add query to history
    users_collection.update_one(
        {"telegram_id": telegram_id},
        {"$push": {"previous_queries": user_query}}
    )

    # Bank-related keywords
    keywords_balance = ["balance", "account balance"]
    keywords_number = ["account number", "acc number", "a/c number"]
    keywords_type = ["account type", "acc type"]
    keywords_all_details = ["all bank details", "full bank details", "all account details", "bank info", "bank information"]

    bank_accounts = user.get("bank_accounts", [])
    has_multiple_accounts = len(bank_accounts) > 1

    # Show specific bank detail
    for account in bank_accounts:
        bank_name = account["bank_name"].lower()

        if bank_name in user_query:
            msg_parts = []
            if any(k in user_query for k in keywords_balance):
                msg_parts.append(f"🏦 Balance in {account['bank_name']} is ₹{account['balance']:,}")
            if any(k in user_query for k in keywords_number):
                msg_parts.append(f"🔢 Account Number: {account['account_number']}")
            if any(k in user_query for k in keywords_type):
                msg_parts.append(f"📘 Account Type: {account['account_type']}")
            if not msg_parts:
                msg_parts.append(
                    f"🏦 {account['bank_name']}:\n🔢 Account Number: {account['account_number']}\n📘 Type: {account['account_type']}\n💰 Balance: ₹{account['balance']:,}"
                )
            await update.message.reply_text("\n".join(msg_parts))
            return

    # If asking for all details
    if any(k in user_query for k in keywords_all_details):
        msg = "🏦 Your Bank Accounts:\n"
        for account in bank_accounts:
            msg += f"\n{account['bank_name']}:\n🔢 Account Number: {account['account_number']}\n📘 Type: {account['account_type']}\n💰 Balance: ₹{account['balance']:,}\n"
        await update.message.reply_text(msg)
        return

    # Generic balance question (no bank specified)
    if any(k in user_query for k in keywords_balance):
        if has_multiple_accounts:
            await update.message.reply_text("🤖 You have multiple accounts. Please specify the bank name (e.g., HDFC, ICICI) to get your balance.")
        else:
            account = bank_accounts[0]
            await update.message.reply_text(
                f"🏦 Your balance in {account['bank_name']} ({account['account_type']}) is ₹{account['balance']:,}"
            )
        return

    # Generic account number / type query (no bank name)
    if any(k in user_query for k in keywords_number + keywords_type):
        if has_multiple_accounts:
            await update.message.reply_text("🤖 You have multiple accounts. Please specify the bank name to get details.")
        else:
            account = bank_accounts[0]
            details = []
            if any(k in user_query for k in keywords_number):
                details.append(f"🔢 Account Number: {account['account_number']}")
            if any(k in user_query for k in keywords_type):
                details.append(f"📘 Account Type: {account['account_type']}")
            await update.message.reply_text("\n".join(details))
        return

    # Personal finance details
    if "credit score" in user_query:
        await update.message.reply_text(f"💳 Your credit score is {user.get('credit_score', 'Not Available')}")
        return

    if "income" in user_query:
        await update.message.reply_text(f"💼 Your monthly income is ₹{user.get('income_monthly', 0):,}")
        return

    if "expenses" in user_query:
        await update.message.reply_text(f"📉 Your monthly expenses are ₹{user.get('expenses_monthly', 0):,}")
        return

    if "loan" in user_query:
        await update.message.reply_text(f"🏦 Your loan status is {user.get('loan_status', 'Not Available')}")
        return

    if "investment" in user_query:
        await update.message.reply_text(f"📊 You're interested in investing in {user.get('investment_interest', 'Not Specified')}")
        return

    if "reminder" in user_query or "frequency" in user_query:
        await update.message.reply_text(f"⏰ Your reminder preference is set to {user.get('reminder_preferences', 'Not Set')}")
        return

    if "phone" in user_query or "contact" in user_query:
        await update.message.reply_text(f"📞 Your registered phone number is {user.get('phone_number', 'Not Available')}")
        return

    if "name" in user_query:
        await update.message.reply_text(f"🧑 Your name is {user.get('name', 'Not Available')}")
        return

    if "age" in user_query:
        await update.message.reply_text(f"🎂 Your age is {user.get('age', 'Not Available')}")
        return
    if "stock" in user_query or "share price" in user_query:
            for word in user_query.split():
                if word.isalpha() and len(word) <= 5:  # crude stock symbol guess
                    stock_info = get_stock_price(word)
                await update.message.reply_text(stock_info)
                return
            await update.message.reply_text("📊 Please mention a valid stock symbol (e.g., TCS, INFY, RELIANCE).")
            return

    # Default: Ask Cohere AI
    prompt = f"You are GenFinBot, a financial assistant.\nUser: {user_query}\nGenFinBot:"
    response = co.generate(
        model='command',
        prompt=prompt,
        max_tokens=200
    )
    ai_reply = response.generations[0].text.strip()

    users_collection.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"last_ai_response": ai_reply}}
    )

    await update.message.reply_text(ai_reply)

# Bot setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 Telegram Bot is running...")
app.run_polling()
