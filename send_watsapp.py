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
T12_API_KEY = os.getenv("T12_API_KEY")

app = Flask(__name__)
client = MongoClient(MONGO_URL)
db = client['genfin_db']
users_collection = db['users']
co = cohere.Client(COHERE_API_KEY)

# In-memory registration state
user_states = {}

HIGH_PRIORITY_KEYWORDS = [
    "fraud", "card stolen", "account hacked", "money stolen",
    "loan default", "missed emi", "credit card lost",
    "debit card lost", "blocked account", "urgent", "immediate help",
    "transaction failed", "unauthorized transaction", "dispute", "payment stuck",
    "loan overdue", "emi overdue"
]

COMPANY_MAPPING = {
    "apple": "AAPL",
    "amazon": "AMZN",
    "infosys": "INFY",
    "reliance": "RELIANCE",
    "hdfc": "HDFC"
}

FAQ_RESPONSES = {
    "what is genfinbot": "🤖 GenFinBot is your AI-powered financial assistant helping you manage bank info, expenses, and investments securely!",
    "how do i check my bank balance": "💰 Simply type your bank name + 'balance', e.g., HDFC balance.",
    "how can i find my account number": "🔢 Type your bank name + 'account number'. Example: ICICI account number.",
    "how can i check my monthly expenses": "📉 Just type 'expenses' to know your recorded monthly expenses.",
    "how does genfinbot handle financial advice": "🧐 GenFinBot uses AI to provide safe, personalized financial suggestions.",
    "is my data secure": "🔐 Yes! Your data is stored securely with encryption.",
    "how can i contact support": "📞 Just type your issue with the keyword 'urgent' or 'high priority'!"
}

def send_email(subject, body, to_email):
    try:
        from_email = os.getenv("EMAIL_SENDER")
        email_password = os.getenv("EMAIL_PASSWORD")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, email_password)
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Error sending email: {str(e)}")

def contains_high_priority(user_query):
    return any(keyword in user_query.lower() for keyword in HIGH_PRIORITY_KEYWORDS)

def get_stock_price(symbol):
    try:
        url = f'https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&apikey={T12_API_KEY}'
        response = requests.get(url)
        data = response.json()
        if 'values' in data:
            price = data['values'][0]['close']
            return f"📈 Current price of {symbol.upper()}: ₹{price}"
        else:
            return "⚠️ No stock data available currently."
    except Exception as e:
        return f"⚠️ Error fetching stock price: {str(e)}"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    from_number = request.form.get("From")
    message_body = request.form.get("Body")
    phone_number = from_number.replace("whatsapp:+91", "")
    resp = MessagingResponse()
    user_query = message_body.strip().lower()
    user = users_collection.find_one({"phone_number": phone_number})

    if not user:
        state = user_states.get(phone_number, {"step": "name"})

        if state["step"] == "name":
            user_states[phone_number] = {"name": message_body.strip(), "step": "age"}
            resp.message("🎂 Enter your age:")

        elif state["step"] == "age":
            try:
                user_states[phone_number]["age"] = int(message_body)
                user_states[phone_number]["step"] = "income"
                resp.message("💼 Enter your monthly income:")
            except:
                resp.message("Please enter a valid age:")

        elif state["step"] == "income":
            try:
                user_states[phone_number]["income_monthly"] = int(message_body)
                user_states[phone_number]["step"] = "expenses"
                resp.message("📉 Enter your monthly expenses:")
            except:
                resp.message("Please enter valid income:")

        elif state["step"] == "expenses":
            try:
                user_states[phone_number]["expenses_monthly"] = int(message_body)
                user_states[phone_number]["step"] = "credit_score"
                resp.message("💳 Enter your credit score:")
            except:
                resp.message("Please enter valid expenses:")

        elif state["step"] == "credit_score":
            try:
                user_states[phone_number]["credit_score"] = int(message_body)
                user_states[phone_number]["step"] = "loan_status"
                resp.message("💰 Loan status (Open/Closed):")
            except:
                resp.message("Please enter valid credit score:")

        elif state["step"] == "loan_status":
            if message_body.lower() in ["open", "closed"]:
                user_states[phone_number]["loan_status"] = message_body.capitalize()
                user_states[phone_number]["step"] = "investment"
                resp.message("📊 What are you interested to invest in?")
            else:
                resp.message("Please type Open/Closed:")

        elif state["step"] == "investment":
            user_states[phone_number]["investment_interest"] = message_body.strip()
            user_states[phone_number]["step"] = "num_accounts"
            resp.message("🏦 How many bank accounts do you have?")

        elif state["step"] == "num_accounts":
            try:
                user_states[phone_number]["remaining_accounts"] = int(message_body)
                user_states[phone_number]["bank_accounts"] = []
                user_states[phone_number]["step"] = "bank_name"
                resp.message("Enter Bank Name for Account 1:")
            except:
                resp.message("Please enter valid number of accounts:")

        elif state["step"] == "bank_name":
            state = user_states[phone_number]
            state["current"] = {"bank_name": message_body}
            state["step"] = "account_number"
            resp.message("Enter Account Number:")

        elif state["step"] == "account_number":
            acc_num = message_body.strip()
            masked = "X" * (len(acc_num) - 4) + acc_num[-4:]
            user_states[phone_number]["current"]["account_number"] = masked
            user_states[phone_number]["step"] = "account_type"
            resp.message("Account Type (Saving/Current):")

        elif state["step"] == "account_type":
            user_states[phone_number]["current"]["account_type"] = message_body
            user_states[phone_number]["step"] = "balance"
            resp.message("Enter Balance:")

        elif state["step"] == "balance":
            try:
                state = user_states[phone_number]
                state["current"]["balance"] = int(message_body)
                state["bank_accounts"].append(state.pop("current"))
                state["remaining_accounts"] -= 1
                if state["remaining_accounts"] > 0:
                    state["step"] = "bank_name"
                    resp.message("Enter next Bank Name:")
                else:
                    final_data = {
                        **{k: v for k, v in state.items() if k not in ["step", "remaining_accounts"]},
                        "phone_number": phone_number,
                        "telegram_id": "Not Linked",
                        "priority": "normal",
                        "previous_queries": []
                    }
                    users_collection.insert_one(final_data)
                    user_states.pop(phone_number)
                    resp.message("✅ Registration done! You can ask about balance, income, expenses, investments!")
            except:
                resp.message("Please enter valid balance:")

        return str(resp)

    # -- If already registered user --
    # Priority detection
    if contains_high_priority(user_query):
        users_collection.update_one({"phone_number": phone_number}, {"$set": {"priority": "high"}})
        send_email("High Priority Alert", f"From {phone_number}: {message_body}", os.getenv("EMAIL_RECEIVER"))
        resp.message("⚠️ High priority issue detected, support alerted!")
        return str(resp)

    # FAQ
    if user_query in FAQ_RESPONSES:
        resp.message(FAQ_RESPONSES[user_query])
        return str(resp)

    # Stocks
    if "stock" in user_query or "share" in user_query:
        for company, symbol in COMPANY_MAPPING.items():
            if company in user_query:
                resp.message(get_stock_price(symbol))
                return str(resp)
        resp.message("Mention valid company name like Apple, Amazon, Infosys.")
        return str(resp)

    # Finance info
    user = users_collection.find_one({"phone_number": phone_number})
    # 5. Fetch Bank Account Details
    if "account number" in user_query or "account type" in user_query or "balance" in user_query:
        bank_accounts = user.get("bank_accounts", [])
    if not bank_accounts:
        resp.message("❗ No bank account data found for you.")
        return str(resp)

    if len(bank_accounts) == 1:
        acc = bank_accounts[0]
        reply_parts = []
        if "account number" in user_query:
            reply_parts.append(f"🔢 Account Number: {acc['account_number']}")
        if "account type" in user_query:
            reply_parts.append(f"📘 Account Type: {acc['account_type']}")
        if "balance" in user_query:
            reply_parts.append(f"💰 Balance: ₹{acc['balance']:,}")

        resp.message("\n".join(reply_parts))
        return str(resp)
    
    else:
        # Multiple accounts: ask which bank
        if any(bank.lower() in user_query for bank in [acc['bank_name'].lower() for acc in bank_accounts]):
            # User already specified bank name
            for acc in bank_accounts:
                if acc['bank_name'].lower() in user_query:
                    reply_parts = []
                    if "account number" in user_query:
                        reply_parts.append(f"🔢 Account Number: {acc['account_number']}")
                    if "account type" in user_query:
                        reply_parts.append(f"📘 Account Type: {acc['account_type']}")
                    if "balance" in user_query:
                        reply_parts.append(f"💰 Balance: ₹{acc['balance']:,}")

                    resp.message("\n".join(reply_parts))
                    return str(resp)

            # If bank not matched
            resp.message("❗Bank name not recognized. Please type the bank name (like HDFC, ICICI, etc.).")
            return str(resp)
        else:
            # No bank name yet
            available_banks = ", ".join([acc['bank_name'] for acc in bank_accounts])
            resp.message(f"🏦 You have multiple bank accounts: {available_banks}. Please mention the bank name you want details for.")
            return str(resp)


    if "income" in user_query:
        resp.message(f"💼 Your monthly income: ₹{user.get('income_monthly', 0):,}")
        return str(resp)

    if "expenses" in user_query:
        resp.message(f"📉 Your monthly expenses: ₹{user.get('expenses_monthly', 0):,}")
        return str(resp)

    if "loan" in user_query:
        resp.message(f"💼 Loan Status: {user.get('loan_status', 'Unknown')}")
        return str(resp)

    if "credit score" in user_query:
        resp.message(f"💳 Credit Score: {user.get('credit_score', 'Unknown')}")
        return str(resp)

    # Cohere fallback
    prompt = f"You are GenFinBot, an intelligent financial bot.\nUser: {message_body}\nGenFinBot:"
    ai = co.generate(model="command", prompt=prompt, max_tokens=200)
    resp.message(ai.generations[0].text.strip())
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
