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

def check_priority_query(msg, user):
    msg = msg.lower()

    if "balance" in msg:
        if "hdfc" in msg:
            for acc in user.get("bank_accounts", []):
                if "hdfc" in acc["bank_name"].lower():
                    return f"🏦 Your HDFC account balance is ₹{acc['balance']}."
        elif "axis" in msg:
            for acc in user.get("bank_accounts", []):
                if "axis" in acc["bank_name"].lower():
                    return f"🏦 Your Axis Bank account balance is ₹{acc['balance']}."
        elif "icici" in msg:
            for acc in user.get("bank_accounts", []):
                if "icici" in acc["bank_name"].lower():
                    return f"🏦 Your ICICI account balance is ₹{acc['balance']}."
        elif "account" in msg:
            return f"💰 Your main account balance is ₹{user.get('balance', 'Not available')}."

    elif "credit score" in msg:
        return f"📊 Your credit score is {user.get('credit_score', 'Not available')}."

    elif "loan" in msg:
        return f"📄 Your current loan status is: {user.get('loan_status', 'Unknown')}."

    elif "investment" in msg:
        return f"📈 You're interested in {user.get('investment_interest', 'no investments yet')}."

    return None

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    from_number = request.form.get("From")  # Format: whatsapp:+91909xxxxxxx
    message_body = request.form.get("Body")
    
    phone_number = from_number.replace("whatsapp:+91", "")

    user = users_collection.find_one({"phone_number": phone_number})
    resp = MessagingResponse()

    if not user:
        resp.message("❗You are not a registered user in the system.")
        return str(resp)

    # Update query history
    users_collection.update_one(
        {"phone_number": phone_number},
        {"$push": {"previous_queries": message_body}}
    )

    # Custom checks first
    priority_reply = check_priority_query(message_body, user)
    if priority_reply:
        users_collection.update_one(
            {"phone_number": phone_number},
            {"$set": {"last_ai_response": priority_reply}}
        )
        resp.message(priority_reply)
        return str(resp)

    # Else, use Cohere for generic queries
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
    app.run(debug=True)
