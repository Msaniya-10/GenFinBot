from flask import Flask, request
from pymongo import MongoClient
import cohere
import os
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Load environment variables
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SUPPORT_EMAIL = os.getenv("EMAIL_RECEIVER")
T12_API_KEY = os.getenv("T12_API_KEY")

# In-memory registration tracker
user_states = {}

# Setup
app = Flask(__name__)
client = MongoClient(MONGO_URL)
db = client['genfin_db']
users_collection = db['users']
co = cohere.Client(COHERE_API_KEY)

# Constants
HIGH_PRIORITY_KEYWORDS = [
    "fraud", "card stolen", "account hacked", "money stolen",
    "loan default", "missed emi", "credit card lost",
    "debit card lost", "blocked account", "urgent", "immediate help",
    "transaction failed", "unauthorized transaction", "dispute", "payment stuck",
    "loan overdue", "emi overdue"
]
# FAQs
FAQ_RESPONSES = {
    "1": "🤖 GenFinBot is your AI-powered financial assistant helping you manage bank info, expenses, and investments securely!",
    "2": "💰 Simply type your bank name + 'balance', e.g., HDFC balance.",
    "3": "🔢 Type your bank name + 'account number'. Example: ICICI account number.",
    "4": "📉 Just type 'expenses' to know your recorded monthly expenses.",
    "5": "🧠 GenFinBot uses AI to provide safe, personalized financial suggestions.",
    "6": "🔐 Yes! Your data is stored securely with encryption.",
    "7": "📞 Just type your issue with the keyword 'urgent' or 'high priority'!"
}
FAQ_QUESTIONS = {
    "faq", "faqs", "faq's", "1", "2", "3", "4", "5", "6", "7",
    "what is genfinbot", "how do i check my bank balance",
    "how can i find my account number", "how can i check my monthly expenses",
    "how does genfinbot handle financial advice", "is my data secure",
    "how can i contact support"
}

COMPANY_MAPPING = {
    "apple": "AAPL",
    "amazon": "AMZN",
    "infosys": "INFY",
    "infy": "INFY",
    "reliance": "RELIANCE",
    "hdfc": "HDFC"
}

# Utilities
def send_email(subject, body):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = SUPPORT_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server.sendmail(EMAIL_SENDER, SUPPORT_EMAIL, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Email error: {e}")

def contains_high_priority(msg):
    return any(k in msg.lower() for k in HIGH_PRIORITY_KEYWORDS)

def get_stock_price(symbol):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&apikey={T12_API_KEY}"
        r = requests.get(url).json()
        if 'values' in r:
            return f"📈 Current price of {symbol.upper()} is ₹{r['values'][0]['close']}"
        else:
            return f"⚠️ Sorry, stock data for {symbol.upper()} is currently unavailable."
    except:
        return f"⚠️ Unable to fetch stock data. Try again later."

# --- Check Priority Queries ---
def check_priority_query(msg, user):
    msg = msg.lower()

    if "balance" in msg:
        for acc in user.get("bank_accounts", []):
            if any(bank in msg for bank in acc["bank_name"].lower().split()):
                return f"🏦 Your {acc['bank_name']} account balance is ₹{acc['balance']}"
    elif "credit score" in msg:
        return f"📊 Your credit score is {user.get('credit_score', 'Not available')}"
    elif "loan" in msg:
        return f"📄 Your current loan status is: {user.get('loan_status', 'Unknown')}"
    elif "investment" in msg:
        return f"📈 You're interested in {user.get('investment_interest', 'no investments yet')}"
    return None

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    from_number = request.form.get("From")  # Format: whatsapp:+91909xxxxxxx
    message_body = request.form.get("Body")
    phone_number = from_number.replace("whatsapp:+91", "")
    user_query = message_body.strip().lower()
    resp = MessagingResponse()

    user = users_collection.find_one({"phone_number": phone_number})

    # 🔁 Registration Flow for New Users
    if not user:
        state = user_states.get(phone_number, {"step": "greet"})

        if state["step"] == "greet":
            user_states[phone_number] = {"step": "name"}
            resp.message("👋 Hello! It looks like you're new here. Let's get you registered. What is your full name?")
            return str(resp)

        elif state["step"] == "name":
            state["name"] = message_body.strip()
            state["step"] = "age"
            user_states[phone_number] = state
            resp.message("🎂 Enter your age:")
            return str(resp)

        elif state["step"] == "age":
            try:
                state["age"] = int(message_body.strip())
                state["step"] = "income"
                resp.message("💼 What's your monthly income?")
            except:
                resp.message("❗ Please enter a valid number for age:")
            return str(resp)

        elif state["step"] == "income":
            try:
                state["income_monthly"] = int(message_body.strip())
                state["step"] = "expenses"
                resp.message("📉 Enter your monthly expenses:")
            except:
                resp.message("❗ Please enter a valid number for income:")
            return str(resp)

        elif state["step"] == "expenses":
            try:
                state["expenses_monthly"] = int(message_body.strip())
                state["step"] = "credit_score"
                resp.message("💳 Enter your credit score:")
            except:
                resp.message("❗ Please enter a valid number for expenses:")
            return str(resp)

        elif state["step"] == "credit_score":
            try:
                state["credit_score"] = int(message_body.strip())
                state["step"] = "loan_status"
                resp.message("📄 What is your loan status? (Open/Closed):")
            except:
                resp.message("❗ Please enter a valid number for credit score:")
            return str(resp)

        elif state["step"] == "loan_status":
            loan = message_body.strip().lower()
            if loan not in ["open", "closed"]:
                resp.message("❗ Please enter 'Open' or 'Closed' for loan status.")
                return str(resp)
            state["loan_status"] = loan.capitalize()
            state["step"] = "investment"
            resp.message("📈 What are you interested in investing in?")
            return str(resp)

        elif state["step"] == "investment":
            state["investment_interest"] = message_body.strip()
            state["step"] = "num_accounts"
            resp.message("🏦 How many bank accounts do you have?")
            return str(resp)

        elif state["step"] == "num_accounts":
            try:
                count = int(message_body.strip())
                state["remaining_accounts"] = count
                state["bank_accounts"] = []
                state["step"] = "bank_name"
                resp.message("🔁 Let's start. Enter Bank Name for Account 1:")
            except:
                resp.message("❗ Please enter a valid number of accounts:")
            return str(resp)

        elif state["step"] == "bank_name":
            state["current_account"] = {"bank_name": message_body.strip()}
            state["step"] = "account_number"
            resp.message("🔢 Enter Account Number:")
            return str(resp)

        elif state["step"] == "account_number":
            acc = message_body.strip()
            masked = "X" * (len(acc) - 4) + acc[-4:]
            state["current_account"]["account_number"] = masked
            state["step"] = "account_type"
            resp.message("📘 Enter Account Type (Saving/Current):")
            return str(resp)

        elif state["step"] == "account_type":
            state["current_account"]["account_type"] = message_body.strip()
            state["step"] = "balance"
            resp.message("💰 Enter Account Balance:")
            return str(resp)

        elif state["step"] == "balance":
            try:
                state["current_account"]["balance"] = int(message_body.strip())
                state["bank_accounts"].append(state["current_account"])
                state.pop("current_account")
                state["remaining_accounts"] -= 1

                if state["remaining_accounts"] > 0:
                    account_no = len(state["bank_accounts"]) + 1
                    state["step"] = "bank_name"
                    resp.message(f"🏦 Enter Bank Name for Account {account_no}:")
                else:
                    final_user = {
                        "phone_number": phone_number,
                        "telegram_id": "Not Linked",
                        "priority": "normal",
                        "previous_queries": [],
                        **{k: v for k, v in state.items() if k not in ["step", "remaining_accounts"]}
                        }
                    users_collection.insert_one(final_user)
                    user_states.pop(phone_number)
                    resp.message("✅ Registration complete! You can now ask anything like 'balance', 'credit score', or 'Can I get a loan?' 💬")
            except:
                resp.message("❗ Please enter a valid number for balance:")
            return str(resp)

    users_collection.update_one(
        {"phone_number": phone_number},
        {"$push": {"previous_queries": message_body}}
    )
    
     # 1. High Priority
    if contains_high_priority(user_query):
        users_collection.update_one({"phone_number": phone_number}, {"$set": {"priority": "high"}})
        subject = f"🚨 High Priority Alert from {phone_number}"
        body = f"User issue: {message_body}"
        send_email(subject, body)
        resp.message("⚠️ We've marked your concern as high priority. Our support team will reach out shortly!")
        return str(resp)
    
    # --- FAQ Menu Trigger ---
    if user_query in {"faq", "faqs", "faq's"}:
        menu = (
            "📋 *FAQ Menu*\n"
            "1. What is GenFinBot?\n"
            "2. How do I check my bank balance?\n"
            "3. How can I find my account number?\n"
            "4. How can I check my monthly expenses?\n"
            "5. How does GenFinBot handle financial advice?\n"
            "6. Is my data secure?\n"
            "7. How can I contact support?\n"
            "\nReply with a question or its number (e.g., 1) to know more."
        )
        resp.message(menu)
        return str(resp)

    if user_query in FAQ_RESPONSES:
        resp.message(FAQ_RESPONSES[user_query])
        return str(resp)

    # --- Bank details ---
    bank_accounts = user.get("bank_accounts", [])
    if any(k in user_query for k in ["balance", "account number", "account type"]):
        if not bank_accounts:
            resp.message("❗ No bank account data found.")
            return str(resp)

        if len(bank_accounts) == 1:
            acc = bank_accounts[0]
            parts = []
            if "account number" in user_query:
                parts.append(f"🔢 Account Number: {acc['account_number']}")
            if "account type" in user_query:
                parts.append(f"📘 Account Type: {acc['account_type']}")
            if "balance" in user_query:
                parts.append(f"💰 Balance: ₹{acc['balance']:,}")
            resp.message("\n".join(parts))
            return str(resp)

        # If multiple accounts
        matched = False
        for acc in bank_accounts:
            if acc["bank_name"].lower() in user_query:
                parts = []
                if "account number" in user_query:
                    parts.append(f"🔢 Account Number: {acc['account_number']}")
                if "account type" in user_query:
                    parts.append(f"📘 Account Type: {acc['account_type']}")
                if "balance" in user_query:
                    parts.append(f"💰 Balance: ₹{acc['balance']:,}")
                resp.message("\n".join(parts))
                matched = True
                break

        if not matched:
            available = ", ".join(acc["bank_name"] for acc in bank_accounts)
            resp.message(f"🏦 You have multiple bank accounts: {available}.\nPlease specify the bank name to proceed.")
        return str(resp)
    
    # 3. Stock info
    if any(k in user_query for k in ["stock", "share", "price"]):
        for company, symbol in COMPANY_MAPPING.items():
            if company in user_query:
                resp.message(get_stock_price(symbol))
                return str(resp)
        resp.message("🔎 Please specify a valid company name like Apple, Amazon, Infosys, etc.")
        return str(resp)

    # 4. Personalized finance info
    keywords = ["loan status", "income", "expenses", "credit score"]
    matched = next((k for k in keywords if k in user_query), None)
    if matched:
        if matched == "loan status":
            resp.message(f"📄 Your loan status is: {user.get('loan_status', 'Unknown')}")
        elif matched == "monthly income":
            resp.message(f"💼 Your monthly income: ₹{user.get('income_monthly', 0):,}")
        elif matched == "monthly expenses":
            resp.message(f"📉 Your monthly expenses: ₹{user.get('expenses_monthly', 0):,}")
        elif matched == "credit score":
            resp.message(f"📊 Your credit score is: {user.get('credit_score', 'Unknown')}")
        elif matched == "investment interest":
            resp.message(f"💰📈 Your credit score is: {user.get('investment_interest', 'Unknown')}")
        return str(resp)

    # 5. Personalized prompt fallback
    context_info = f"User is {user.get('age')} years old with income ₹{user.get('income_monthly', 0):,}, expenses ₹{user.get('expenses_monthly', 0):,}, credit score {user.get('credit_score')}, loan status {user.get('loan_status')}, and investment interest: {user.get('investment_interest')}."
    prompt = f"You are GenFinBot, a financial expert.\n{context_info}\nUser: {message_body}\nGenFinBot:"

    response = co.generate(model="command", prompt=prompt, max_tokens=200)
    reply = response.generations[0].text.strip()

    users_collection.update_one(
        {"phone_number": phone_number},
        {"$push": {"previous_queries": message_body}, "$set": {"last_ai_response": reply}}
    )
    resp.message(reply)
    return str(resp)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
