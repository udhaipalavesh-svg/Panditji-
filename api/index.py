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
                    from google import genai
                    
                    # 1. Check if the API key is accessible from Vercel Environment Variables
                    gemini_key = os.environ.get("GEMINI_API_KEY")
                    if not gemini_key:
                        send_message(chat_id, "Error: Vercel cannot find your GEMINI_API_KEY. Please check your Vercel Environment Variables.")
                        return jsonify(status="success"), 200
                        
                    # 2. Pass the key explicitly to the GenAI client
                    gemini_client = genai.Client(api_key=gemini_key)
                    
                    prompt = f"""
                    You are Panditji, an expert Vedic Astrologer. 
                    A user has provided the following birth details: {user_text}.
                    
                    Based on these details:
                    1. Briefly mention their key astrological placements.
                    2. Deduce an intuitive reading of their current life situation based on standard astrological transit knowledge.
                    3. Provide an insightful and grounded prediction for their near future.
                    
                    Speak directly to the user in a mystical but clear tone. Keep the entire response under 250 words so it is easy to read on Telegram.
                    """
                    
                    # 3. Generate response using gemini-2.0-flash
                    response = gemini_client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt
                    )
                    
                    send_message(chat_id, response.text)
                    
                except Exception as e:
                    # 4. Report exact exception back to Telegram to identify any API issue
                    send_message(chat_id, f"The stars are cloudy. Technical Error: {str(e)}")
                
        return jsonify(status="success"), 200
        
