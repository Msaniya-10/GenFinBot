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

user_states = {}

HIGH_PRIORITY_KEYWORDS = [
    "fraud", "card stolen", "account hacked", "money stolen",
    "loan default", "missed emi", "credit card lost", "debit card lost",
    "blocked account", "urgent", "immediate help", "transaction failed",
    "unauthorized transaction", "dispute", "payment stuck", "loan overdue", "emi overdue"
]

COMPANY_MAPPING = {
    "apple": "AAPL",
    "amazon": "AMZN",
    "infosys": "INFY",
    "infy": "INFY",
    "reliance": "RELIANCE",
    "hdfc": "HDFC"
}

FAQ_RESPONSES = {
    "what is genfinbot": "🤖 GenFinBot is your AI-powered financial assistant helping you manage bank info, expenses, and investments securely!",
    "how do i check my bank balance": "💰 Simply type your bank name + 'balance', e.g., HDFC balance.",
    "how can i find my account number": "🔢 Type your bank name + 'account number'. Example: ICICI account number.",
    "how can i check my monthly expenses": "📉 Just type 'expenses' to know your recorded monthly expenses.",
    "how does genfinbot handle financial advice": "🧠 GenFinBot uses AI to provide safe, personalized financial suggestions.",
    "is my data secure": "🔒 Yes! Your data is stored securely with encryption.",
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
    return any(keyword in user_query for keyword in HIGH_PRIORITY_KEYWORDS)

def get_stock_price(symbol):
    try:
        url = f'https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&apikey={T12_API_KEY}'
        response = requests.get(url)
        data = response.json()
        if 'values' in data:
            price = data['values'][0]['close']
            return f"📈 The current price of {symbol.upper()} is ₹{price}."
        else:
            return f"⚠ No stock data available for {symbol.upper()} right now."
    except Exception as e:
        return f"⚠ Error fetching stock data: {str(e)}"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    from_number = request.form.get("From")
    message_body = request.form.get("Body")
    phone_number = from_number.replace("whatsapp:+91", "")
    resp = MessagingResponse()
    user_query = message_body.strip().lower()

    user = users_collection.find_one({"phone_number": phone_number})

    # Registration
    if not user:
        state = user_states.get(phone_number, "start")

        if state == "start":
            user_states[phone_number] = "name"
            resp.message("👤 Welcome to GenFinBot! What's your full name?")
            return str(resp)

        elif state == "name":
            if len(message_body) < 2:
                resp.message("❗Please enter a valid full name:")
            else:
                user_states[phone_number] = {"name": message_body.strip()}
                resp.message("🎂 Enter your age:")
            return str(resp)

        elif isinstance(state, dict) and "name" in state and "age" not in state:
            try:
                age = int(message_body)
                state["age"] = age
                user_states[phone_number] = state
                resp.message("💼 Enter your monthly income:")
            except ValueError:
                resp.message("❗Please enter a valid number for age:")
            return str(resp)

        elif isinstance(state, dict) and "age" in state and "income_monthly" not in state:
            try:
                income = int(message_body)
                state["income_monthly"] = income
                user_states[phone_number] = state
                resp.message("📉 Enter your monthly expenses:")
            except ValueError:
                resp.message("❗Please enter a valid number for income:")
            return str(resp)

        elif isinstance(state, dict) and "income_monthly" in state and "expenses_monthly" not in state:
            try:
                expenses = int(message_body)
                state["expenses_monthly"] = expenses
                user_states[phone_number] = state
                resp.message("💳 What's your credit score?")
            except ValueError:
                resp.message("❗Please enter a valid number for expenses:")
            return str(resp)

        elif isinstance(state, dict) and "expenses_monthly" in state and "credit_score" not in state:
            try:
                credit_score = int(message_body)
                state["credit_score"] = credit_score
                user_states[phone_number] = state
                resp.message("💰 What's your loan status? (Open/Closed)")
            except ValueError:
                resp.message("❗Please enter a valid number for credit score:")
            return str(resp)

        elif isinstance(state, dict) and "credit_score" in state and "loan_status" not in state:
            loan_status = message_body.lower()
            if loan_status in ["open", "closed"]:
                state["loan_status"] = loan_status.capitalize()
                user_states[phone_number] = state
                resp.message("📊 What are you interested to invest in?")
            else:
                resp.message("❗Please type Open or Closed.")
            return str(resp)

        elif isinstance(state, dict) and "loan_status" in state and "investment_interest" not in state:
            investment = message_body.strip()
            state["investment_interest"] = investment
            # Insert user
            final_user = {
                "phone_number": phone_number,
                "telegram_id": "Not Linked",
                "mode": "real",
                "priority": "normal",
                "previous_queries": [],
                "bank_accounts": [],
                **state
            }
            users_collection.insert_one(final_user)
            user_states.pop(phone_number)
            resp.message("✅ Registration complete! You can now ask me anything 💬")
            return str(resp)

    # FAQs
    if user_query in FAQ_RESPONSES:
        resp.message(FAQ_RESPONSES[user_query])
        return str(resp)

    # High Priority
    if contains_high_priority(user_query):
        users_collection.update_one({"phone_number": phone_number}, {"$set": {"priority": "high"}})
        send_email("High Priority Alert", f"User {phone_number} reported:\n{message_body}", os.getenv("EMAIL_RECEIVER"))
        resp.message("⚠ High-priority issue detected. Support alerted!")
        return str(resp)

    # Stock Price
    if "stock" in user_query or "share" in user_query or "price" in user_query:
        for company, symbol in COMPANY_MAPPING.items():
            if company in user_query:
                stock_response = get_stock_price(symbol)
                resp.message(stock_response)
                return str(resp)
        resp.message("📊 Please mention a valid company like Apple, Amazon, Infosys.")
        return str(resp)

    # Financial Info
    if "balance" in user_query:
        bank_accounts = user.get("bank_accounts", [])
        if bank_accounts:
            balances = [f"{acc['bank_name']}: ₹{acc['balance']:,}" for acc in bank_accounts]
            resp.message("🏦 Your Bank Balances:\n" + "\n".join(balances))
        else:
            resp.message("❗No bank accounts found.")
        return str(resp)

    if "income" in user_query:
        resp.message(f"💼 Monthly Income: ₹{user.get('income_monthly', 'Unknown'):,}")
        return str(resp)

    if "expenses" in user_query:
        resp.message(f"📉 Monthly Expenses: ₹{user.get('expenses_monthly', 'Unknown'):,}")
        return str(resp)

    if "loan" in user_query:
        resp.message(f"🏦 Loan Status: {user.get('loan_status', 'Unknown')}")
        return str(resp)

    if "credit score" in user_query:
        resp.message(f"💳 Credit Score: {user.get('credit_score', 'Unknown')}")
        return str(resp)

    # Fallback - AI
    prompt = f"You are GenFinBot, a smart financial assistant.\nUser: {message_body}\nGenFinBot:"
    response = co.generate(model="command", prompt=prompt, max_tokens=200)
    ai_reply = response.generations[0].text.strip()

    users_collection.update_one(
        {"phone_number": phone_number},
        {"$push": {"previous_queries": message_body}, "$set": {"last_ai_response": ai_reply}}
    )

    resp.message(ai_reply)
    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
