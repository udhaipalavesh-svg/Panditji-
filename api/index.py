import os
import requests
import re
from flask import Flask, request, jsonify
from datetime import datetime
import swisseph as swe
import jyotichart as chart

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def send_document(chat_id, file_path):
    """Sends the generated SVG chart to Telegram"""
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': chat_id}
        requests.post(f"{TELEGRAM_API_URL}/sendDocument", data=data, files=files)

@app.route('/api', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Vercel Webhook is Active", 200
        
    if request.method == 'POST':
        update = request.get_json()
        
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            if user_text.startswith("/start"):
                welcome_msg = "Welcome! Please send your birth details in this format: DD-MM-YYYY Time (e.g., 26-03-1982 05:00)"
                send_message(chat_id, welcome_msg)
            else:
                send_message(chat_id, "Calculating exact planetary degrees and drawing your chart...")

                try:
                    # 1. Parse Date and Time (Basic Regex extraction)
                    match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})', user_text)
                    if not match:
                        send_message(chat_id, "Please use the exact format: DD-MM-YYYY HH:MM")
                        return jsonify(status="success"), 200
                        
                    day, month, year, hour, minute = map(int, match.groups())
                    
                    # 2. Astronomical Calculations with Pysweph
                    swe.set_ephe_path(None) # Use built-in Moshier ephemeris
                    
                    # Convert to UTC (Assuming IST for this prototype: subtract 5.5 hours)
                    utc_time = swe.utc_time_zone(year, month, day, hour, minute, 0, 5.5)
                    jdet, jdut = swe.utc_to_jd(*utc_time)
                    
                    # Calculate Sun and Moon degrees as an example
                    sun_pos, _ = swe.calc_ut(jdut, swe.SUN, swe.FLG_SWIEPH)
                    moon_pos, _ = swe.calc_ut(jdut, swe.MOON, swe.FLG_SWIEPH)
                    
                    # 3. Draw Chart with Jyotichart
                    # Initialize North Indian Chart (Diamond style)
                    north = chart.NorthChart("D1 Natal", "User Chart")
                    north.set_birth_details(f"{day}-{month}-{year}", f"{hour}:{minute}", "IST")
                    
                    # Add planets (Simplified mapping for example)
                    # jyotichart uses zodiac signs 1-12, so we roughly estimate based on degree
                    sun_sign = int(sun_pos[0] / 30) + 1
                    moon_sign = int(moon_pos[0] / 30) + 1
                    north.set_ascendantsign("Aries") # Hardcoded for prototype; requires precise geocoding to calculate dynamically
                    north.add_planet(chart.SUN, "Su", sun_sign)
                    north.add_planet(chart.MOON, "Mo", moon_sign)
                    
                    # Save to Vercel's temporary directory
                    svg_path = "/tmp/natal_chart.svg"
                    north.draw("/tmp/", "natal_chart", "svg")
                    
                    # Send chart to user
                    send_document(chat_id, svg_path)

                    # 4. Deep Analysis via Gemini
                    gemini_key = os.environ.get("GEMINI_API_KEY")
                    today_date = datetime.now().strftime("%B %d, %Y")
                    
                    prompt = f"""
                    You are Panditji. Today is {today_date}.
                    A user provided birth details: {user_text}.
                    
                    My Python backend calculated their exact positions:
                    - Sun is at {sun_pos[0]:.2f} degrees of the zodiac.
                    - Moon is at {moon_pos[0]:.2f} degrees of the zodiac.
                    
                    Provide a concise Vedic reading focusing on their Sun/Moon dynamic, and apply the current transit of Jupiter to their life right now. Keep it under 200 words.
                    """
                    
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                    response = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
                    
                    if response.status_code == 200:
                        send_message(chat_id, response.json()['candidates'][0]['content']['parts'][0]['text'])
                    else:
                        send_message(chat_id, "API Error during analysis.")
                        
                except Exception as e:
                    send_message(chat_id, f"Technical Error: {str(e)}")
                
        return jsonify(status="success"), 200
        
