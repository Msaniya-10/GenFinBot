from flask import Flask, request, jsonify
from pymongo import MongoClient
import cohere
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Setup Cohere and MongoDB
co = cohere.Client(os.getenv("COHERE_API_KEY"))
mongo_url = os.getenv("MONGO_URL")
client = MongoClient(mongo_url)
db = client['genfin_db']
users_collection = db['users']

@app.route('/ask_ai', methods=['POST'])
def ask_ai():
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    user = users_collection.find_one({"user_id": user_id})
    if not user or 'queries' not in user or not user['queries']:
        return jsonify({"error": "User not found or no queries available"}), 404

    user_query = user['queries'][-1]

    try:
        response = co.generate(
            model='command',  # or 'command-light'
            prompt=f"You are GenFinBot, a financial advisor.\nUser: {user_query}\nGenFinBot:",
            max_tokens=200
        )
        reply = response.generations[0].text.strip()

        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"last_ai_response": reply}}
        )

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
