import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Fetch secrets from Vercel
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def send_message(chat_id, text):
    """Helper function to send a message back to the user"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

@app.route('/api', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Vercel Webhook is Active", 200
        
    if request.method == 'POST':
        update = request.get_json()
        
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            if user_text == "/start":
                welcome_msg = "Welcome! Please send your birth details in this format: DD-MM-YYYY Time City (e.g., 01-01-1980 05:00 Chandigarh)"
                send_message(chat_id, welcome_msg)
            
            else:
                send_message(chat_id, "Consulting the stars and calculating your chart. Please wait a moment...")

                try:
                    gemini_key = os.environ.get("GEMINI_API_KEY")
                    if not gemini_key:
                        send_message(chat_id, "Error: Vercel cannot find your GEMINI_API_KEY.")
                        return jsonify(status="success"), 200
                        
                    prompt = f"""
                    You are Panditji, an expert Vedic Astrologer. 
                    A user has provided the following birth details: {user_text}.
                    
                    Based on these details:
                    1. Briefly mention their key astrological placements.
                    2. Deduce an intuitive reading of their current life situation based on standard astrological transit knowledge.
                    3. Provide an insightful and grounded prediction for their near future.
                    
                    Speak directly to the user in a mystical but clear tone. Keep the entire response under 250 words so it is easy to read on Telegram.
                    """
                    
                    # Bypass the Google library and talk directly to the server
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                    headers = {"Content-Type": "application/json"}
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}]
                    }
                    
                    # Send the request
                    response = requests.post(gemini_url, headers=headers, json=payload)
                    response_data = response.json()
                    
                    # Read the response directly
                    if response.status_code == 200:
                        ai_text = response_data['candidates'][0]['content']['parts'][0]['text']
                        send_message(chat_id, ai_text)
                    else:
                        # If Google rejects it, get the raw error message
                        error_msg = response_data.get('error', {}).get('message', 'Unknown API Error')
                        send_message(chat_id, f"Google API Error: {error_msg}")
                    
                except Exception as e:
                    send_message(chat_id, f"The stars are cloudy. Technical Error: {str(e)}")
                
        return jsonify(status="success"), 200
        
