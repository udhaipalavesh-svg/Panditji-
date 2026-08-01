import os
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# Fetch secrets from Vercel Environment Variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Initialize the Gemini AI Client
try:
    # This automatically looks for GEMINI_API_KEY in Vercel's environment variables
    gemini_client = genai.Client()
except Exception as e:
    gemini_client = None

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
            
            if user_text == "/start":
                welcome_msg = "Welcome! Please send your birth details in this format: Date Time City (e.g., 26-03-1982 05:00 Chandigarh)"
                send_message(chat_id, welcome_msg)
            else:
                if gemini_client is None:
                    send_message(chat_id, "Astrology AI is currently unavailable. Please check your Gemini API key in Vercel.")
                    return jsonify(status="success"), 200

                # Send a quick holding message so the user knows it is working
                send_message(chat_id, "Consulting the stars and calculating your chart. Please wait a moment...")

                # Construct the prompt instructing Gemini on how to behave
                prompt = f"""
                You are Panditji, an expert Vedic Astrologer. 
                A user has provided the following birth details: {user_text}.
                
                Based on these details, please do the following:
                1. Briefly mention their key astrological placements (Lagna, Moon Sign, etc.).
                2. Deduce an intuitive reading of their current life situation based on standard astrological transit knowledge.
                3. Provide an insightful and grounded prediction for their near future.
                
                Speak directly to the user in a mystical but clear tone. Keep the entire response under 250 words so it is easy to read on Telegram.
                """
                
                try:
                    # Ask Gemini to generate the prediction
                    response = gemini_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    # Send Gemini's prediction back to Telegram
                    send_message(chat_id, response.text)
                    
                except Exception as e:
                    send_message(chat_id, "The stars are cloudy right now. I could not generate a reading.")
                    print(f"Gemini Error: {e}")
                
        return jsonify(status="success"), 200
        
