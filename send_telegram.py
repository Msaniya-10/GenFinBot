from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from pymongo import MongoClient
import cohere
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")

# Setup
co = cohere.Client(COHERE_API_KEY)
client = MongoClient(MONGO_URL)
db = client["genfin_db"]
users_collection = db["users"]

# Clean welcome message
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I'm GenFinBot, your AI finance assistant 💰. Ask me anything related to banking, investment, or finance!")

# Handle user queries with condition-based replies
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.message.chat.id)
    user_query = update.message.text.lower()

    user = users_collection.find_one({"telegram_id": telegram_id})
    if not user:
        await update.message.reply_text("❗You are not a registered user in the system.")
        return

    # Add query to previous_queries
    users_collection.update_one(
        {"telegram_id": telegram_id},
        {"$push": {"previous_queries": user_query}}
    )

    # Check for specific keywords in query
    if "balance" in user_query:
        if "account" in user_query:
            reply = f"🏦 Your main account balance is ₹{user.get('balance', 'N/A')}."
        elif "hdfc" in user_query.lower() or "sbi" in user_query.lower():
            bank_name = "HDFC" if "hdfc" in user_query else "SBI"
            for acct in user.get("bank_accounts", []):
                if bank_name.lower() in acct['bank_name'].lower():
                    reply = f"🏦 Your {bank_name} account balance is ₹{acct['balance']}."
                    break
            else:
                reply = f"⚠️ No {bank_name} account found in your profile."
        else:
            reply = f"🏦 Your account balance is ₹{user.get('balance', 'N/A')}."

    elif "credit score" in user_query:
        reply = f"💳 Your credit score is {user.get('credit_score', 'N/A')}."

    elif "loan" in user_query:
        reply = f"🏛️ Your loan status is: {user.get('loan_status', 'N/A')}."

    elif "reminder" in user_query:
        reply = f"🔔 You have chosen {user.get('reminder_preferences', 'N/A')} reminders for payments."

    elif "investment" in user_query:
        reply = f"📈 You're interested in investing in {user.get('investment_interest', 'N/A')}."

    elif "income" in user_query:
        reply = f"💰 Your monthly income is ₹{user.get('income_monthly', 'N/A')}."

    elif "expense" in user_query or "spend" in user_query:
        reply = f"💸 Your monthly expenses are ₹{user.get('expenses_monthly', 'N/A')}."

    else:
        # Use Cohere if no specific match found
        prompt = f"You are GenFinBot, a financial advisor.\nUser: {user_query}\nGenFinBot:"
        response = co.generate(model='command', prompt=prompt, max_tokens=200)
        reply = response.generations[0].text.strip()

    # Save AI response
    users_collection.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"last_ai_response": reply}}
    )

    await update.message.reply_text(reply)

# Bot setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 Telegram Bot is running...")
app.run_polling()
