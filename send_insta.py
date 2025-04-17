import requests

ACCESS_TOKEN = 'YOUR_LONG_LIVED_ACCEEAAOgFNj2ir4BOZCVcaz9yaDhmxUGAnE0UtX1UbKBtqlNkJkoX49NkNzmkah2GQGuPpiSVY3JlSZCeLwpHRqkpGunykWdVXrec8jZBLyCWrDtcZC6JKSJu3EhugMov7DAo10yuRAM0fKGeIP9xQbZAZB80Ve0rw51lLuFZC0cKrE74zy16Jf6ADCnOLCexh8jKzxkrW95uj05dya8oQ3kJt0bfIz8gZDZDSS_TOKEN'
IG_USER_ID = '122105069492826011'
RECIPIENT_ID = 'USER_ID_OF_RECIPIENT'  # You get this from webhook/messages
MESSAGE_TEXT = 'Hello from my bot!'

url = f'https://graph.facebook.com/v19.0/{IG_USER_ID}/messages'

payload = {
    'messaging_product': 'instagram',
    'recipient': {'id': RECIPIENT_ID},
    'message': {'text': MESSAGE_TEXT},
    'access_token': ACCESS_TOKEN
}

response = requests.post(url, json=payload)
print(response.status_code)
print(response.json())
