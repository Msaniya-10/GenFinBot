from flask import Flask, request
from pymongo import MongoClient
import cohere
import os
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse

# Load environment variables
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# Setup
app = Flask(__name__)
client = MongoClient(MONGO_URL)
db = client['genfin_db']
users_collection = db['users']
co = cohere.Client(COHERE_API_KEY)

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

    if not user:
        resp.message("❗You are not a registered user in the system.")
        return str(resp)

    users_collection.update_one(
        {"phone_number": phone_number},
        {"$push": {"previous_queries": message_body}}
    )

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

    # --- Default to Cohere ---
    prompt = f"You are GenFinBot, a financial advisor.\nUser: {message_body}\nGenFinBot:"
    response = co.generate(
        model="command",
        prompt=prompt,
        max_tokens=200
    )
    ai_reply = response.generations[0].text.strip()

    users_collection.update_one(
        {"phone_number": phone_number},
        {"$set": {"last_ai_response": ai_reply}}
    )

    resp.message(ai_reply)
    return str(resp)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
