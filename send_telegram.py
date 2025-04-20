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

co = cohere.Client(COHERE_API_KEY)
client = MongoClient(MONGO_URL)
db = client["genfin_db"]
users_collection = db["users"]

# Greet command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I'm GenFinBot, your AI finance assistant 💰. Ask me anything related to banking, investment, or finance!")

# Stock price function
def get_stock_price(symbol):
    symbols_to_try = [symbol.upper(), symbol.upper() + ".BSE", symbol.upper() + ".NS"]
    for sym in symbols_to_try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": sym,
            "apikey": ALPHA_VANTAGE_KEY
        }
        response = requests.get(url, params=params)
        data = response.json()
        if "Global Quote" in data and data["Global Quote"].get("05. price"):
            price = data["Global Quote"]["05. price"]
            change = data["Global Quote"]["10. change percent"]
            return f"📈 {sym} is trading at ₹{float(price):,.2f} ({change})"
    return "⚠️ Invalid stock symbol or data not available."

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.message.chat.id)
    user_query = update.message.text.lower()
    user = users_collection.find_one({"telegram_id": telegram_id})

    if not user:
        await update.message.reply_text("❗You are not a registered user in the system.")
        return

    users_collection.update_one({"telegram_id": telegram_id}, {"$push": {"previous_queries": user_query}})
    bank_accounts = user.get("bank_accounts", [])
    has_multiple = len(bank_accounts) > 1

    # Bank-related queries
    balance_keys = ["balance"]
    number_keys = ["account number"]
    type_keys = ["account type"]
    all_info_keys = ["all bank details", "bank info", "account details"]

    for account in bank_accounts:
        bank = account["bank_name"].lower()
        if bank in user_query:
            parts = []
            if any(k in user_query for k in balance_keys):
                parts.append(f"🏦 Balance in {account['bank_name']}: ₹{account['balance']:,}")
            if any(k in user_query for k in number_keys):
                parts.append(f"🔢 Account Number: {account['account_number']}")
            if any(k in user_query for k in type_keys):
                parts.append(f"📘 Account Type: {account['account_type']}")
            if not parts:
                parts.append(f"{account['bank_name']}: ₹{account['balance']:,}, {account['account_number']} ({account['account_type']})")
            await update.message.reply_text("\n".join(parts))
            return

    if any(k in user_query for k in all_info_keys):
        reply = "🏦 Your Bank Accounts:\n"
        for a in bank_accounts:
            reply += f"\n{a['bank_name']}:\n🔢 {a['account_number']}\n📘 {a['account_type']}\n💰 ₹{a['balance']:,}\n"
        await update.message.reply_text(reply)
        return

    if any(k in user_query for k in balance_keys):
        if has_multiple:
            await update.message.reply_text("🤖 You have multiple accounts. Please mention the bank name.")
        else:
            a = bank_accounts[0]
            await update.message.reply_text(f"🏦 Your balance in {a['bank_name']}: ₹{a['balance']:,}")
        return

    if any(k in user_query for k in number_keys + type_keys):
        if has_multiple:
            await update.message.reply_text("🤖 You have multiple accounts. Please mention the bank name.")
        else:
            a = bank_accounts[0]
            parts = []
            if any(k in user_query for k in number_keys):
                parts.append(f"🔢 Account Number: {a['account_number']}")
            if any(k in user_query for k in type_keys):
                parts.append(f"📘 Account Type: {a['account_type']}")
            await update.message.reply_text("\n".join(parts))
        return

    # Personal financial info
    if "credit score" in user_query:
        await update.message.reply_text(f"💳 Your credit score: {user.get('credit_score', 'N/A')}")
        return
    if "income" in user_query:
        await update.message.reply_text(f"💼 Monthly income: ₹{user.get('income_monthly', 0):,}")
        return
    if "expenses" in user_query:
        await update.message.reply_text(f"📉 Monthly expenses: ₹{user.get('expenses_monthly', 0):,}")
        return
    if "loan" in user_query:
        await update.message.reply_text(f"🏦 Loan status: {user.get('loan_status', 'N/A')}")
        return
    if "investment" in user_query:
        await update.message.reply_text(f"📊 Interested in: {user.get('investment_interest', 'N/A')}")
        return
    if "reminder" in user_query:
        await update.message.reply_text(f"⏰ Reminder frequency: {user.get('reminder_preferences', 'N/A')}")
        return
    if "phone" in user_query:
        await update.message.reply_text(f"📞 Phone: {user.get('phone_number', 'N/A')}")
        return
    if "name" in user_query:
        await update.message.reply_text(f"🧑 Name: {user.get('name', 'N/A')}")
        return
    if "age" in user_query:
        await update.message.reply_text(f"🎂 Age: {user.get('age', 'N/A')}")
        return

    # Stock query
    if "stock" in user_query or "share price" in user_query:
        for word in user_query.split():
            if word.isalpha() and len(word) <= 5:
                await update.message.reply_text(get_stock_price(word))
                return
        await update.message.reply_text("📊 Please mention a valid stock symbol (e.g., TCS, INFY).")
        return

    # Cohere fallback
    prompt = f"You are GenFinBot, a financial advisor.\nUser: {user_query}\nGenFinBot:"
    response = co.generate(model="command", prompt=prompt, max_tokens=200)
    reply = response.generations[0].text.strip()

    users_collection.update_one({"telegram_id": telegram_id}, {"$set": {"last_ai_response": reply}})
    await update.message.reply_text(reply)

# Start bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 Telegram Bot is running...")
app.run_polling()
