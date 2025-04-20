from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from pymongo import MongoClient
import cohere
import finnhub
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# Setup clients
co = cohere.Client(COHERE_API_KEY)
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
client = MongoClient(MONGO_URL)
db = client["genfin_db"]
users_collection = db["users"]

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I'm GenFinBot, your AI finance assistant 💰. Ask me anything related to banking, investment, or finance!")

# Function to fetch live stock price using Finnhub
def get_stock_price(symbol):
    try:
        quote = finnhub_client.quote(symbol.upper())
        current = quote["c"]
        change = quote["dp"]
        if current:
            return f"📈 {symbol.upper()} is trading at ₹{current:,.2f} ({change:.2f}% change)"
        else:
            return "⚠️ Stock symbol not found or no price data available."
    except Exception as e:
        return f"⚠️ Error fetching data: {str(e)}"

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.message.chat.id)
    user_query = update.message.text.lower()
    user = users_collection.find_one({"telegram_id": telegram_id})

    if not user:
        await update.message.reply_text("❗You are not a registered user in the system.")
        return

    users_collection.update_one(
        {"telegram_id": telegram_id},
        {"$push": {"previous_queries": user_query}}
    )

    # Check bank-related keywords
    keywords_balance = ["balance"]
    keywords_number = ["account number", "acc number", "a/c number"]
    keywords_type = ["account type"]
    keywords_all = ["all bank details", "bank info"]

    bank_accounts = user.get("bank_accounts", [])
    multiple = len(bank_accounts) > 1

    for account in bank_accounts:
        bank = account["bank_name"].lower()
        if bank in user_query:
            msg = []
            if any(k in user_query for k in keywords_balance):
                msg.append(f"🏦 Balance in {account['bank_name']}: ₹{account['balance']:,}")
            if any(k in user_query for k in keywords_number):
                msg.append(f"🔢 Account Number: {account['account_number']}")
            if any(k in user_query for k in keywords_type):
                msg.append(f"📘 Account Type: {account['account_type']}")
            if not msg:
                msg.append(
                    f"🏦 {account['bank_name']}:\n🔢 Account Number: {account['account_number']}\n📘 Type: {account['account_type']}\n💰 Balance: ₹{account['balance']:,}"
                )
            await update.message.reply_text("\n".join(msg))
            return

    if any(k in user_query for k in keywords_all):
        reply = "🏦 Your Bank Accounts:\n"
        for acc in bank_accounts:
            reply += f"\n{acc['bank_name']}:\n🔢 {acc['account_number']}\n📘 {acc['account_type']}\n💰 ₹{acc['balance']:,}\n"
        await update.message.reply_text(reply)
        return

    if any(k in user_query for k in keywords_balance):
        if multiple:
            await update.message.reply_text("🤖 You have multiple accounts. Please specify the bank name.")
        else:
            acc = bank_accounts[0]
            await update.message.reply_text(f"🏦 Your balance in {acc['bank_name']}: ₹{acc['balance']:,}")
        return

    if any(k in user_query for k in keywords_number + keywords_type):
        if multiple:
            await update.message.reply_text("🤖 You have multiple accounts. Please specify the bank name.")
        else:
            acc = bank_accounts[0]
            reply = []
            if any(k in user_query for k in keywords_number):
                reply.append(f"🔢 Account Number: {acc['account_number']}")
            if any(k in user_query for k in keywords_type):
                reply.append(f"📘 Account Type: {acc['account_type']}")
            await update.message.reply_text("\n".join(reply))
        return

    # Personal Info
    if "credit score" in user_query:
        await update.message.reply_text(f"💳 Credit Score: {user.get('credit_score', 'Not Available')}")
        return
    if "income" in user_query:
        await update.message.reply_text(f"💼 Monthly Income: ₹{user.get('income_monthly', 0):,}")
        return
    if "expenses" in user_query:
        await update.message.reply_text(f"📉 Monthly Expenses: ₹{user.get('expenses_monthly', 0):,}")
        return
    if "loan" in user_query:
        await update.message.reply_text(f"🏦 Loan Status: {user.get('loan_status', 'N/A')}")
        return
    if "investment" in user_query:
        await update.message.reply_text(f"📊 Investment Preference: {user.get('investment_interest', 'N/A')}")
        return
    if "reminder" in user_query:
        await update.message.reply_text(f"⏰ Reminder: {user.get('reminder_preferences', 'Not Set')}")
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

    # Stock query (e.g. stock TCS or price RELIANCE)
    if "stock" in user_query or "share" in user_query or "price" in user_query:
        for word in user_query.split():
            if word.isalpha() and len(word) <= 6:
                stock_response = get_stock_price(word)
                await update.message.reply_text(stock_response)
                return
        await update.message.reply_text("📊 Please provide a valid stock symbol like TCS or INFY.")
        return

    # Otherwise ask Cohere
    prompt = f"You are GenFinBot, a financial advisor.\nUser: {user_query}\nGenFinBot:"
    response = co.generate(model='command', prompt=prompt, max_tokens=200)
    reply = response.generations[0].text.strip()

    users_collection.update_one({"telegram_id": telegram_id}, {"$set": {"last_ai_response": reply}})
    await update.message.reply_text(reply)

# App start
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 GenFinBot Telegram is live...")
app.run_polling()
