import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Fetch secrets from Vercel Environment Variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def send_message(chat_id, text):
    """Helper function to send a message back to the user"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

@app.route('/', methods=['POST', 'GET'])
def webhook():
    # If Vercel checks the endpoint, return OK
    if request.method == 'GET':
        return "Vercel Webhook is Active", 200
        
    # Process incoming Telegram messages
    if request.method == 'POST':
        update = request.get_json()
        
        # Check if the update contains a message
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            # Basic routing logic
            if user_text == "/start":
                welcome_msg = "Welcome! Please send your birth details in this format: Date Time City (e.g., 15-01-1990 10:30 New Delhi)"
                send_message(chat_id, welcome_msg)
            else:
                response_msg = f"I received your data: {user_text}. I am calculating your chart now."
                send_message(chat_id, response_msg)
                
        return jsonify(status="success"), 200
      
