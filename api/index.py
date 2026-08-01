import os
import requests
import re
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
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
                    # 1. Parse Date and Time
                    match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})', user_text)
                    if not match:
                        send_message(chat_id, "Please use the exact format: DD-MM-YYYY HH:MM")
                        return jsonify(status="success"), 200
                        
                    day, month, year, hour, minute = map(int, match.groups())
                    
                    # 2. Astronomical Calculations with Pysweph
                    swe.set_ephe_path(None)
                    
                    # Use Python's built-in datetime for safe UTC conversion (assuming IST input)
                    dt_ist = datetime(year, month, day, hour, minute)
                    dt_utc = dt_ist - timedelta(hours=5, minutes=30)
                    utc_decimal_hour = dt_utc.hour + (dt_utc.minute / 60.0)
                    
                    # Calculate Julian Date safely
                    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal_hour)
                    
                    # Safely calculate planetary positions by capturing the entire output
                    sun_calc = swe.calc_ut(jdut, swe.SUN)
                    moon_calc = swe.calc_ut(jdut, swe.MOON)
                    
                    # Dynamically extract longitude depending on how the specific library fork formats it
                    sun_lon = sun_calc[0] if isinstance(sun_calc[0], float) else sun_calc[0][0]
                    moon_lon = moon_calc[0] if isinstance(moon_calc[0], float) else moon_calc[0][0]
                    
                    # 3. Draw Chart with Jyotichart
                    # The correct initialization format according to the documentation:
                    # chart.NorthChart("Chart Title", "User Name")
                    north = chart.NorthChart("Natal Chart", f"{day}-{month}-{year} {hour}:{minute} IST", IsFullChart=False) 
                    
                    sun_sign = int(sun_lon / 30) + 1
                    moon_sign = int(moon_lon / 30) + 1
                    north.set_ascendantsign("Aries") # Placeholder until geocoding is added
                    north.add_planet(chart.SUN, "Su", sun_sign)
                    north.add_planet(chart.MOON, "Mo", moon_sign)
                    
                    svg_path = "/tmp/natal_chart.svg"
                    
                    # Ensure the output directory exists
                    os.makedirs("/tmp", exist_ok=True)
                    
                    # The draw method takes the output directory, file name (without extension), and optionally the format.
                    north.draw("/tmp/", "natal_chart") 
                    
                    send_document(chat_id, svg_path)

                    # 4. Deep Analysis via Gemini
                    gemini_key = os.environ.get("GEMINI_API_KEY")
                    today_date = datetime.now().strftime("%B %d, %Y")
                    
                    prompt = f"""
                    You are Panditji. Today is {today_date}.
                    A user provided birth details: {user_text}.
                    
                    My Python backend calculated their exact positions:
                    - Sun is at {sun_lon:.2f} degrees of the zodiac.
                    - Moon is at {moon_lon:.2f} degrees of the zodiac.
                    
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
        
