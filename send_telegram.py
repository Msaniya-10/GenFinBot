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

# ✅ Welcome message
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I'm GenFinBot, your AI finance assistant 💰. Ask me anything related to banking, investment, or finance!")

# 💬 Handle user messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.message.chat.id)
    user_query = update.message.text.lower().strip()

    user = users_collection.find_one({"telegram_id": telegram_id})
    if not user:
        await update.message.reply_text("❗You are not a registered user in the system.")
        return

    # 🏦 Check if query asks for account details
    if "account details" in user_query or "my balance" in user_query or "bank details" in user_query:
        account_info = user.get("bank_accounts", [])
        if account_info:
            account = account_info[0]  # Use the first account
            details_msg = (
                f"📄 *Account Details:*\n"
                f"👤 *Name:* {user.get('name', 'N/A')}\n"
                f"🏦 *Bank Name:* {account.get('bank_name', 'N/A')}\n"
                f"💳 *Account Number:* {account.get('account_number', 'N/A')}\n"
                f"💼 *Account Type:* {account.get('account_type', 'N/A')}\n"
                f"💰 *Balance:* ₹{account.get('balance', 'N/A')}"
            )
            await update.message.reply_text(details_msg, parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ No bank account information found.")
        return

    # 🧠 Add query to previous_queries
    users_collection.update_one(
        {"telegram_id": telegram_id},
        {"$push": {"previous_queries": user_query}}
    )

    # 🔮 AI response using Cohere
    prompt = f"You are GenFinBot, a financial advisor.\nUser: {user_query}\nGenFinBot:"
    response = co.generate(
        model='command',
        prompt=prompt,
        max_tokens=200
    )
    ai_reply = response.generations[0].text.strip()

    # Save AI reply
    users_collection.update_one(
        {"telegram_id": telegram_id},
        {"$set": {"last_ai_response": ai_reply}}
    )

    await update.message.reply_text(ai_reply)

# 🚀 Bot setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 Telegram Bot is running...")
app.run_polling()
