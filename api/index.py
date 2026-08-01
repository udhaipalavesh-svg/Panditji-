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

@app.route('/api', methods=['POST', 'GET'])
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
            
            # 1. INSTANT REPLY FOR /START
            if user_text == "/start":
                welcome_msg = "Welcome! Please send your birth details in this format: DD-MM-YYYY Time City (e.g., 26-03-1982 05:00 Chandigarh)"
                send_message(chat_id, welcome_msg)
            
            # 2. HEAVY AI PROCESSING FOR CHARTS
            else:
                send_message(chat_id, "Consulting the stars and calculating your chart. Please wait a moment...")

                try:
                    # Lazy-load the AI client to keep /start lightning fast
                    from google import genai
                    gemini_client = genai.Client()
                    
                    prompt = f"""
                    You are Panditji, an expert Vedic Astrologer. 
                    A user has provided the following birth details: {user_text}.
                    
                    Based on these details, please do the following:
                    1. Briefly mention their key astrological placements (Lagna, Moon Sign, etc.).
                    2. Deduce an intuitive reading of their current life situation based on standard astrological transit knowledge.
                    3. Provide an insightful and grounded prediction for their near future.
                    
                    Speak directly to the user in a mystical but clear tone. Keep the entire response under 250 words so it is easy to read on Telegram.
                    """
                    
                    # Ask Gemini to generate the prediction using the stable 2.0 model
                    response = gemini_client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt
                    )
                    
                    # Send Gemini's prediction back to Telegram
                    send_message(chat_id, response.text)
                    
                except Exception as e:
                    send_message(chat_id, "The stars are cloudy right now. I could not generate a reading.")
                    print(f"Gemini Error: {e}")
                
        return jsonify(status="success"), 200
        
