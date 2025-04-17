from flask import Flask, request
import requests
import json

app = Flask(__name__)

VERIFY_TOKEN = 'saniya_secret_token'
ACCESS_TOKEN = 'EAAOgFNj2ir4BO28GFtcIgCLSOdzF28VbBPhGZBaYlAh2Wddsl2viWqLkBEfLQYuk0OyTYSKJ8PcEOSuNOZCrmVfBWodf5N89cEgwvO76l88Ik90nOv4L583q085dpNSI7HNjZACG7sDL4uRhoM8ADyjzV92NZA5Mcd9XOblUZCN5xIWhOQ0wVaAZCsT8TptIhLMZCZCt36Gsgv0RIC8WDBMuRHub2si7V10QSjQZD'

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("✅ Webhook verified!")
            return challenge, 200
        else:
            return 'Verification failed', 403

    elif request.method == 'POST':
        print("✅ POST received from Meta")
        data = request.get_json()
        print("📥 Full Webhook Payload:", json.dumps(data, indent=4))

        try:
            sender_id = data['entry'][0]['messaging'][0]['sender']['id']
            message_text = data['entry'][0]['messaging'][0]['message']['text']
            print("✅ Sender ID:", sender_id)
            print("💬 Message Text:", message_text)

            # Now send a reply message
            reply_text = f"You said: {message_text}"

            url = f"https://graph.facebook.com/v19.0/{sender_id}/messages"
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_type": "RESPONSE",
                "recipient": {"id": sender_id},
                "message": {"text": reply_text},
                "access_token": ACCESS_TOKEN
            }

            response = requests.post(url, headers=headers, json=payload)
            print("➡️ Sent reply:", response.text)

        except Exception as e:
            print("⚠️ Failed to extract data or send reply:", e)

        return 'Event received', 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)
