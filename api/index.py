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

# Category mappings with astrological focal points
CATEGORIES = {
    "edu": ("🎓 Education", "4th & 5th houses, Mercury and Jupiter. Focus on studies, learning, exams, and skill development."),
    "car": ("💼 Career", "10th, 6th & 11th houses, Saturn and Sun. Focus on job growth, status, workplace dynamics, and promotions."),
    "fin": ("💰 Finances", "2nd & 11th houses, Jupiter and Venus. Focus on accumulated wealth, cash flow, and financial gains."),
    "hea": ("🏥 Health", "1st & 6th houses, Sun and Moon. Focus on physical vitality, immunity, lifestyle wellness, and mental energy."),
    "rel": ("❤️ Relationships", "5th & 7th houses, Venus. Focus on romance, emotional bonding, and attraction."),
    "mar": ("💍 Marriage", "7th & 9th houses, Venus and Jupiter. Focus on marital harmony, spouse dynamics, and long-term partnership."),
    "fam": ("🏡 Family", "2nd & 4th houses, Moon and Jupiter. Focus on domestic peace, family bond, and domestic life."),
    "tra": ("✈️ Foreign Travel", "9th & 12th houses, Rahu and Moon. Focus on foreign movement, long journeys, visa prospects, and settlement."),
    "pro": ("🏠 Property & Vehicles", "4th house, Mars and Venus. Focus on land, home purchase, real estate, and vehicle comfort."),
    "spi": ("🧘 Spiritual Growth", "8th, 9th & 12th houses, Ketu and Jupiter. Focus on inner peace, meditation, and karmic clearing."),
    "obs": ("⚖️ Obstacles & Debts", "6th & 8th houses, Saturn and Mars. Focus on clearing legal issues, debts, competition, and hidden blocks."),
    "chi": ("👶 Children & Progeny", "5th house, Jupiter. Focus on children's well-being, growth, and creative progeny."),
    "men": ("🧠 Mental Peace", "4th & 12th houses, Moon and Mercury. Focus on emotional stability, anxiety relief, and inner tranquility.")
}

def send_message(chat_id, text, reply_markup=None):
    """Sends a standard text message with optional interactive buttons"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def send_document(chat_id, file_path):
    """Sends the generated SVG chart to Telegram"""
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': chat_id}
        requests.post(f"{TELEGRAM_API_URL}/sendDocument", data=data, files=files)

def answer_callback(callback_id, text=""):
    """Acknowledges a button click to stop the loading spinner in Telegram"""
    requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json={"callback_query_id": callback_id, "text": text})

def calculate_positions(day, month, year, hour, minute):
    """Helper function to calculate Sun & Moon coordinates"""
    swe.set_ephe_path(None)
    dt_ist = datetime(year, month, day, hour, minute)
    dt_utc = dt_ist - timedelta(hours=5, minutes=30)
    utc_decimal = dt_utc.hour + (dt_utc.minute / 60.0)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal)
    
    sun_calc = swe.calc_ut(jdut, swe.SUN)
    moon_calc = swe.calc_ut(jdut, swe.MOON)
    
    sun_lon = sun_calc[0] if isinstance(sun_calc[0], float) else sun_calc[0][0]
    moon_lon = moon_calc[0] if isinstance(moon_calc[0], float) else moon_calc[0][0]
    
    return sun_lon, moon_lon

def build_menu_keyboard(day, month, year, hour, minute):
    """Generates the Inline Keyboard containing category buttons with encoded birth details"""
    date_str = f"{day:02d}{month:02d}{year}"
    time_str = f"{hour:02d}{minute:02d}"
    
    keyboard = [
        [
            {"text": "🎓 Education", "callback_data": f"cat:edu|{date_str}|{time_str}"},
            {"text": "💼 Career", "callback_data": f"cat:car|{date_str}|{time_str}"}
        ],
        [
            {"text": "💰 Finances", "callback_data": f"cat:fin|{date_str}|{time_str}"},
            {"text": "🏥 Health", "callback_data": f"cat:hea|{date_str}|{time_str}"}
        ],
        [
            {"text": "❤️ Relationships", "callback_data": f"cat:rel|{date_str}|{time_str}"},
            {"text": "💍 Marriage", "callback_data": f"cat:mar|{date_str}|{time_str}"}
        ],
        [
            {"text": "🏡 Family", "callback_data": f"cat:fam|{date_str}|{time_str}"},
            {"text": "✈️ Travel", "callback_data": f"cat:tra|{date_str}|{time_str}"}
        ],
        [
            {"text": "🏠 Property", "callback_data": f"cat:pro|{date_str}|{time_str}"},
            {"text": "🧘 Spiritual", "callback_data": f"cat:spi|{date_str}|{time_str}"}
        ],
        [
            {"text": "⚖️ Obstacles", "callback_data": f"cat:obs|{date_str}|{time_str}"},
            {"text": "👶 Children", "callback_data": f"cat:chi|{date_str}|{time_str}"}
        ],
        [
            {"text": "🧠 Mental Peace", "callback_data": f"cat:men|{date_str}|{time_str}"}
        ]
    ]
    return {"inline_keyboard": keyboard}

@app.route('/api', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Vercel Webhook is Active", 200
        
    if request.method == 'POST':
        update = request.get_json()
        gemini_key = os.environ.get("GEMINI_API_KEY")
        today_date = datetime.now().strftime("%B %d, %Y")

        # --- HANDLE INLINE BUTTON CLICKS ---
        if "callback_query" in update:
            cb = update["callback_query"]
            chat_id = cb["message"]["chat"]["id"]
            data = cb["data"]
            answer_callback(cb["id"], "Consulting the stars...")

            try:
                # Parse callback data: cat:code|DDMMYYYY|HHMM
                cat_code, date_part, time_part = data.replace("cat:", "").split("|")
                day, month, year = int(date_part[:2]), int(date_part[2:4]), int(date_part[4:])
                hour, minute = int(time_part[:2]), int(time_part[2:])
                
                cat_name, cat_focus = CATEGORIES.get(cat_code, ("🔮 General", "General life guidance"))
                sun_lon, moon_lon = calculate_positions(day, month, year, hour, minute)
                
                prompt = f"""
                You are Panditji, an expert Vedic Astrologer. Today's date is {today_date}.
                A user has requested a deep-dive reading for: **{cat_name}**.
                
                Birth Details: {day:02d}-{month:02d}-{year} {hour:02d}:{minute:02d} IST.
                Calculated Planetary Positions:
                - Sun is at {sun_lon:.2f}° of the zodiac.
                - Moon is at {moon_lon:.2f}° of the zodiac.
                
                Astrological Focus for this query: {cat_focus}
                
                Structure your response into 3 distinct sections:
                1. **Current Analysis**: Intuitive insight into their current state in this domain based on placements and major transits (like Jupiter and Saturn).
                2. **Forecast**: Clear, grounded predictions for the next 3 to 6 months.
                3. **Vedic Remedies (Upayas)**: Provide 2 safe, highly practical, non-gemstone remedies (e.g., Karma adjustment, simple Mantra chant, specific Daan/Charity, or Fasting/Color therapy). Do NOT prescribe gemstones.
                
                Tone: Empathetic, respectful, mystical yet clear. Use relevant emojis. Keep under 250 words.
                """

                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                res = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
                
                if res.status_code == 200:
                    ai_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                    # Re-attach menu keyboard so user can easily tap another domain
                    menu = build_menu_keyboard(day, month, year, hour, minute)
                    send_message(chat_id, ai_text, reply_markup=menu)
                else:
                    send_message(chat_id, "The stars are cloudy right now. Please try again.")

            except Exception as e:
                send_message(chat_id, f"Error processing selection: {str(e)}")

            return jsonify(status="success"), 200

        # --- HANDLE DIRECT TEXT MESSAGES ---
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            if user_text.startswith("/start"):
                welcome_msg = "Welcome! Please send your birth details in this format: DD-MM-YYYY HH:MM (e.g., 05-09-1981 12:16)"
                send_message(chat_id, welcome_msg)
            else:
                send_message(chat_id, "Calculating exact planetary degrees and generating your birth chart...")

                try:
                    match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})', user_text)
                    if not match:
                        send_message(chat_id, "Please use the exact format: DD-MM-YYYY HH:MM (e.g., 05-09-1981 12:16)")
                        return jsonify(status="success"), 200
                        
                    day, month, year, hour, minute = map(int, match.groups())
                    sun_lon, moon_lon = calculate_positions(day, month, year, hour, minute)
                    
                    # Generate SVG Chart
                    north = chart.NorthChart("Natal Chart", f"{day:02d}-{month:02d}-{year}", IsFullChart=False)
                    sun_sign = int(sun_lon / 30) + 1
                    moon_sign = int(moon_lon / 30) + 1
                    north.set_ascendantsign("Aries")
                    north.add_planet(chart.SUN, "Su", sun_sign)
                    north.add_planet(chart.MOON, "Mo", moon_sign)
                    
                    os.makedirs("/tmp", exist_ok=True)
                    svg_path = "/tmp/natal_chart.svg"
                    north.draw("/tmp/", "natal_chart")
                    send_document(chat_id, svg_path)

                    # Initial General Overview Prompt
                    prompt = f"""
                    You are Panditji. Today's date is {today_date}.
                    Birth Details: {user_text}.
                    Calculated Positions: Sun = {sun_lon:.2f}°, Moon = {moon_lon:.2f}°.
                    
                    Provide a warm, concise general overview of their natal Sun/Moon dynamic and current major transit themes. 
                    Keep it under 150 words. Invite them to select a specific life category below for a deeper reading.
                    """

                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                    res = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
                    
                    menu = build_menu_keyboard(day, month, year, hour, minute)
                    
                    if res.status_code == 200:
                        ai_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                        send_message(chat_id, ai_text, reply_markup=menu)
                    else:
                        send_message(chat_id, "Select a specific category below to view your domain reading:", reply_markup=menu)

                except Exception as e:
                    send_message(chat_id, f"Technical Error: {str(e)}")
                
        return jsonify(status="success"), 200
        
