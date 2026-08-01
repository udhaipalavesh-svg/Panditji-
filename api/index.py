import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime  # Added this to grab the exact current date

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
                        
                    # 1. Grab today's exact date so the AI knows the present timeline
                    today_date = datetime.now().strftime("%B %d, %Y")
                    
                    # 2. Upgraded prompt for strict timelines and better astrological refinement
                    prompt = f"""
                    You are Panditji, an expert Vedic Astrologer. 
                    Today's exact date is {today_date}. You must base all current transit calculations and future predictions from this date forward. Do not reference past years as the present.
                    
                    A user has provided the following birth details: {user_text}.
                    
                    Based on these details, please provide a highly refined, accurate astrological reading:
                    1. Core Placements: Reveal their Lagna (Ascendant), Moon Sign, and one key strength in their birth chart.
                    2. Current Transits: Provide an intuitive reading of their life right now based on major planetary transits (like Saturn or Jupiter) relative to {today_date}.
                    3. Future Guidance: Provide a grounded, insightful prediction for the next 6 to 12 months.
                    
                    Speak directly to the user in a mystical, empathetic, but clear tone. Use emojis tastefully. Keep the entire response nicely formatted and strictly under 250 words so it is easy to read on Telegram.
                    """
                    
                    # Target the newest, active gemini-3.6-flash model endpoint
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                    headers = {"Content-Type": "application/json"}
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}]
                    }
                    
                    # Send the request directly to Google
                    response = requests.post(gemini_url, headers=headers, json=payload)
                    response_data = response.json()
                    
                    if response.status_code == 200:
                        ai_text = response_data['candidates'][0]['content']['parts'][0]['text']
                        send_message(chat_id, ai_text)
                    else:
                        error_msg = response_data.get('error', {}).get('message', 'Unknown API Error')
                        send_message(chat_id, f"Google API Error: {error_msg}")
                    
                except Exception as e:
                    send_message(chat_id, f"The stars are cloudy. Technical Error: {str(e)}")
                
        return jsonify(status="success"), 200
        
