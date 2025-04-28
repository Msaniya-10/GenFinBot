from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from pymongo import MongoClient
import cohere
import os
from dotenv import load_dotenv
import requests
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters,ConversationHandler)
from telegram import ReplyKeyboardMarkup, KeyboardButton


# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")
T12_API_KEY = os.getenv("T12_API_KEY")

# Setup clients
co = cohere.Client(COHERE_API_KEY)
client = MongoClient(MONGO_URL)
db = client["genfin_db"]
users_collection = db["users"]

# Email setup
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# 🚫 Spam keywords
SPAM_KEYWORDS = ["JetonVPNbot", "t.me/", "VPN", "пробный период", "instagram", "youtube", "http", "https"]

#Registration states
(MODE, NAME, AGE, INCOME, EXPENSES, CREDIT_SCORE, LOAN_STATUS, INVESTMENT, NUM_ACCOUNTS, BANK_DETAILS) = range(10)
user_registration_data = {}

# --- Utility Functions ---
def contains_high_priority(message: str) -> bool:
    message = message.lower()

    keyword_groups = [
        ["fraud"],
        ["card", "stolen"],
        ["account", "hacked"],
        ["money", "stolen"],
        ["loan", "default"],
        ["missed", "emi"],
        ["credit", "card", "lost"],
        ["debit", "card", "lost"],
        ["blocked", "account"],
        ["urgent"],
        ["immediate", "help"],
        ["transaction", "failed"],
        ["unauthorized", "transaction"],
        ["dispute"],
        ["payment", "stuck"],
        ["loan", "overdue"],
        ["emi", "overdue"],
    ]

    for group in keyword_groups:
        if all(word in message for word in group):
            return True

    return False


def send_priority_email(user_name, telegram_id, message_text):
    try:
        subject = f"🚨 High Priority Alert from {user_name} (ID: {telegram_id})"
        body = f"User {user_name} (Telegram ID: {telegram_id}) reported an issue:\n\n\"{message_text}\""

        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print("📧 High priority email sent!")
    except Exception as e:
        print(f"⚠️ Failed to send email: {e}")

# --- Registration Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.message.chat.id)
    user = users_collection.find_one({"telegram_id": telegram_id})

    if not user:
        await update.message.reply_text("🛂 Please choose how you want to proceed:\n\nType `Real` to register as a real user.\nType `Test` to explore in demo mode.")
        return MODE
    else:
        await update.message.reply_text("👋 Welcome back! How can I assist you today?")
        return ConversationHandler.END

async def capture_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = update.message.text.strip().lower()
    telegram_id = str(update.message.chat.id)

    if mode == "test":
        existing = users_collection.find_one({"telegram_id": telegram_id})
        if existing:
             await update.message.reply_text("🧪 You're already in demo mode. Feel free to continue testing!")
             return ConversationHandler.END
        else:
            demo_user = {
            "telegram_id": telegram_id,
            "name": "Demo User",
            "age": 30,
            "income_monthly": 50000,
            "expenses_monthly": 30000,
            "credit_score": 750,
            "loan_status": "Closed",
            "investment_interest": "Stocks",
            "phone_number": "Not Provided",
            "mode": "test",
            "priority": "normal",
            "previous_queries": [],
            "bank_accounts": [
                {
                    "bank_name": "Demo Bank",
                    "account_number": "0000000000",
                    "account_type": "Savings",
                    "balance": 100000
                }
            ]
        }
        users_collection.insert_one(demo_user)
        await update.message.reply_text("✅ Demo mode activated. You are now registered with test data. Feel free to explore!")
        return ConversationHandler.END

    elif mode == "real":
        await update.message.reply_text("👤 Great! Please enter your full name:")
        return NAME
    else:
        await update.message.reply_text("❗Please type either `Real` or `Test` to continue.")
        return MODE

async def capture_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❗Please enter a valid full name:")
        return NAME
    user_registration_data[update.message.chat.id] = {"name": name}
    await update.message.reply_text("🎂 Enter your age:")
    return AGE

async def capture_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        age = int(update.message.text)
        user_registration_data[chat_id]["age"] = age
        await update.message.reply_text("💼 Enter your monthly income:")
        return INCOME
    except ValueError:
        await update.message.reply_text("❗Please enter a valid number for age:")
        return AGE

async def capture_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        income = int(update.message.text)
        user_registration_data[chat_id]["income_monthly"] = income
        await update.message.reply_text("📉 Enter your monthly expenses:")
        return EXPENSES
    except ValueError:
        await update.message.reply_text("❗Please enter a valid number for income:")
        return INCOME

async def capture_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        expenses = int(update.message.text)
        user_registration_data[chat_id]["expenses_monthly"] = expenses
        await update.message.reply_text("💳 What's your credit score?")
        return CREDIT_SCORE
    except ValueError:
        await update.message.reply_text("❗Please enter a valid number for expenses:")
        return EXPENSES

async def capture_credit_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        score = int(update.message.text)
        user_registration_data[chat_id]["credit_score"] = score
        await update.message.reply_text("💰 What's your loan status (Open/Closed)?")
        return LOAN_STATUS
    except ValueError:
        await update.message.reply_text("❗Please enter a valid number for credit score:")
        return CREDIT_SCORE

async def capture_loan_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loan_status = update.message.text.strip().lower()
    if loan_status not in ["open", "closed"]:
        await update.message.reply_text("❗Please type either 'Open' or 'Closed' for your loan status:")
        return LOAN_STATUS
    user_registration_data[update.message.chat.id]["loan_status"] = loan_status.capitalize()
    await update.message.reply_text("📊 What are you interested in investing in?")
    return INVESTMENT

async def capture_investment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    investment = update.message.text.strip()
    if len(investment) < 2:
        await update.message.reply_text("❗Please enter a valid investment preference (like 'Stocks', 'Mutual Funds', etc.):")
        return INVESTMENT
    user_registration_data[update.message.chat.id]["investment_interest"] = investment
    await update.message.reply_text("🏦 How many bank accounts do you have?")
    return NUM_ACCOUNTS

async def capture_num_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text)
        context.user_data["remaining_accounts"] = count
        context.user_data["bank_accounts"] = []
        await update.message.reply_text("🏦 Enter Bank Name for Account 1:")
        return BANK_DETAILS
    except ValueError:
        await update.message.reply_text("❗Please enter a valid number of accounts:")
        return NUM_ACCOUNTS
async def capture_bank_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    data = context.user_data

    if "current_detail" not in data:
        data["current_detail"] = {"bank_name": text}
        await update.message.reply_text("🔢 Enter Account Number:")
        return BANK_DETAILS

    if "account_number" not in data["current_detail"]:
        # Mask the account number (keep only last 4 digits visible)
        account_number = text.strip()
        if len(account_number) > 4:
            masked_account_number = "X" * (len(account_number) - 4) + account_number[-4:]
        else:
            masked_account_number = account_number  # If too short, keep as is

        data["current_detail"]["account_number"] = masked_account_number
        await update.message.reply_text("📘 Enter Account Type (Saving/Current):")
        return BANK_DETAILS

    if "account_type" not in data["current_detail"]:
        data["current_detail"]["account_type"] = text
        await update.message.reply_text("💰 Enter Balance:")
        return BANK_DETAILS

    try:
        data["current_detail"]["balance"] = int(text)
    except ValueError:
        await update.message.reply_text("❗Please enter a valid number for balance:")
        return BANK_DETAILS

    # Save current bank account
    data["bank_accounts"].append(data["current_detail"])
    data.pop("current_detail")
    data["remaining_accounts"] -= 1

    if data["remaining_accounts"] > 0:
        acc_no = len(data["bank_accounts"]) + 1
        await update.message.reply_text(f"🏦 Enter Bank Name for Account {acc_no}:")
        return BANK_DETAILS
    else:
        full_data = user_registration_data[update.message.chat.id]
        full_data.update({
            "telegram_id": str(update.message.chat.id),
            "phone_number": "Not Provided",
            "bank_accounts": data["bank_accounts"]
        })
        users_collection.insert_one(full_data)
        await update.message.reply_text("✅ You are now registered! Ask me anything about your finances 💬")
        return ConversationHandler.END

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.message.chat.id)
    result = users_collection.delete_one({"telegram_id": telegram_id})
    if result.deleted_count > 0:
        await update.message.reply_text("✅ Your data has been reset. Please type /start to register again!")
    else:
        await update.message.reply_text("⚠️ No existing data found to reset. You can directly type /start.")

# --- Standard message processing after registration ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text
    telegram_id = str(update.message.chat.id)
    
    company_mapping = {
            "apple": "AAPL",
            "amazon": "AMZN",
            "infosys": "INFY",
            "infy": "INFY",
            "reliance": "RELIANCE",
            "hdfc": "HDFC"
        }

    # Block spam
    if any(word.lower() in user_query.lower() for word in SPAM_KEYWORDS):
        print("🚫 Spam detected!")
        return

    user = users_collection.find_one({"telegram_id": telegram_id})
    if not user:
        await update.message.reply_text("❗Please type /start to register first.")
        return

    # FAQ menu trigger
    if user_query.strip().lower() in ["faq", "faqs", "faq's"]:
        faq_buttons = [
            [KeyboardButton("📄 What is GenFinBot?")],
            [KeyboardButton("🏦 How do I check my bank balance?")],
            [KeyboardButton("💳 How can I find my account number?")],
            [KeyboardButton("💰 How can I check my monthly expenses?")],
            [KeyboardButton("🧠 How does GenFinBot handle financial advice?")],
            [KeyboardButton("🔐 Is my data secure?")],
            [KeyboardButton("❓ How can I contact support?")]
        ]
        reply_markup = ReplyKeyboardMarkup(faq_buttons, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Here are some frequently asked questions 👇🏻 Choose one:", reply_markup=reply_markup)
        return

    # FAQ answer handling
    if user_query == "📄 What is GenFinBot?":
        await update.message.reply_text("GenFinBot is your AI-powered financial assistant helping you manage bank info, expenses, investments securely!")
        return

    if user_query == "🏦 How do I check my bank balance?":
        await update.message.reply_text("Simply type your bank name + 'balance', for example: HDFC balance or ICICI balance.")
        return

    if user_query == "💳 How can I find my account number?":
        await update.message.reply_text("Ask about your bank account number by typing the bank name + 'account number'. Example: HDFC account number.")
        return

    if user_query == "💰 How can I check my monthly expenses?":
        await update.message.reply_text("Just type 'expenses' and GenFinBot will tell you your recorded monthly expenses.")
        return

    if user_query == "🧠 How does GenFinBot handle financial advice?":
        await update.message.reply_text("GenFinBot uses AI and your profile context to provide personalized, safe financial suggestions.")
        return

    if user_query == "🔐 Is my data secure?":
        await update.message.reply_text("Yes! All your data is stored securely in encrypted databases. We respect your privacy.")
        return

    if user_query == "❓ How can I contact support?":
        await update.message.reply_text("You can type 'high priority' along with your issue to notify our support team instantly.")
        return

     # ⚡ High-priority detection
    if contains_high_priority(user_query):
        users_collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"priority": "high"}}
        )
        await update.message.reply_text("⚠️ This seems like a high-priority issue. Our support team has been notified.")
        
        user_name = user.get("name", "Unknown User")  # If name not available, use placeholder
        send_priority_email(user_name, telegram_id, user_query)
        return

    # Log the query
    users_collection.update_one(
        {"telegram_id": telegram_id},
        {"$push": {"previous_queries": user_query}}
    )

    # Bank-related keywords
    keywords_balance = ["balance"]
    keywords_number = ["account number", "acc number", "a/c number"]
    keywords_type = ["account type"]
    keywords_all = ["all bank details", "bank info"]

    bank_accounts = user.get("bank_accounts", [])
    multiple = len(bank_accounts) > 1

    for account in bank_accounts:
        bank = account["bank_name"].lower()
        if bank in user_query.lower():
            msg = []
            if any(k in user_query for k in keywords_balance):
                msg.append(f"🏦 Balance in {account['bank_name']}: ₹{account['balance']:,}")
            if any(k in user_query for k in keywords_number):
                msg.append(f"🔢 Account Number: {account['account_number']}")
            if any(k in user_query for k in keywords_type):
                msg.append(f"📘 Account Type: {account['account_type']}")
            if not msg:
                msg.append(
                    f"🏦 {account['bank_name']}:\n🔢 {account['account_number']}\n📘 {account['account_type']}\n💰 ₹{account['balance']:,}"
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

    # Personal info
    if "credit score" in user_query:
        await update.message.reply_text(f"💳 Credit Score: {user.get('credit_score', 'Not Available')}")
        return

    if "income" in user_query:
        await update.message.reply_text(f"💼 Monthly Income: ₹{user.get('income_monthly', 0):,}")
        return

    if "expenses" in user_query:
        await update.message.reply_text(f"📉 Monthly Expenses: ₹{user.get('expenses_monthly', 0):,}")
        return

    if "loan status" in user_query:
        await update.message.reply_text(f"🏦 Loan Status: {user.get('loan_status', 'N/A')}")
        return

    if "investment" in user_query:
        await update.message.reply_text(f"📊 Investment Preference: {user.get('investment_interest', 'N/A')}")
        return

    if "reminder" in user_query:
        await update.message.reply_text(f"⏰ Reminder Preference: {user.get('reminder_preferences', 'Not Set')}")
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

    # Stock
    if any(word in user_query.lower() for word in ["stock", "share", "price"]):
        found = False
        for company, symbol in company_mapping.items():
            if company in user_query.lower():
                stock_response = get_stock_price(symbol)
                await update.message.reply_text(stock_response)
                found = True
                break

        if not found:
            await update.message.reply_text("📊 Please provide a valid company name like Apple, Amazon, TCS, Infosys, or Reliance.")
        return


    # ✨ Cohere AI Response
    age = user.get("age", "unknown")
    income = user.get("income_monthly", "unknown")
    expenses = user.get("expenses_monthly", "unknown")
    credit_score = user.get("credit_score", "unknown")
    loan_status = user.get("loan_status", "unknown")
    investment_pref = user.get("investment_interest", "unknown")

# Format numbers safely
    def format_number(val):
        if isinstance(val, (int, float)):
            return f"₹{val:,}"
        else:
            return str(val)

    context_info = (
        f"The user is {age} years old with a monthly income of {format_number(income)} and expenses of {format_number(expenses)}. "
        f"Their credit score is {credit_score}, loan status is '{loan_status}', and investment interest is '{investment_pref}'."
        )


    prompt = (
        f"You are GenFinBot, an intelligent financial assistant.\n"
        f"{context_info}\n"
        f"User: {user_query}\n"
        f"GenFinBot:"
    )

    response = co.generate(model='command', prompt=prompt, max_tokens=200)
    reply = response.generations[0].text.strip()

    users_collection.update_one({"telegram_id": telegram_id}, {"$set": {"last_ai_response": reply}})
    await update.message.reply_text(reply)

# Function to fetch live stock price using Twelve Data API
def get_stock_price(symbol):
    try:
        url = f'https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&apikey={T12_API_KEY}'
        response = requests.get(url)
        data = response.json()
        if 'values' in data:
            stock_data = data['values'][0]
            price = stock_data['close']
            return f"📈 The current price of {symbol.upper()} is ₹{price}."
        else:
            return f"⚠️ No stock data available for {symbol.upper()}. Please try again later."
    except Exception as e:
        return f"⚠️ Error fetching stock data: {str(e)}"

# --- Main App ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_mode)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_name)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_age)],
        INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_income)],
        EXPENSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_expenses)],
        CREDIT_SCORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_credit_score)],
        LOAN_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_loan_status)],
        INVESTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_investment)],
        NUM_ACCOUNTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_num_accounts)],
        BANK_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, capture_bank_details)],
    },
    fallbacks=[]
)

app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler('reset', reset))

print("🚀 GenFinBot Telegram is live...")
app.run_polling()
