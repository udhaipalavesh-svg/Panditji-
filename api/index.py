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

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

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
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def send_document(chat_id, file_path):
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': chat_id}
        requests.post(f"{TELEGRAM_API_URL}/sendDocument", data=data, files=files)

def answer_callback(callback_id, text=""):
    requests.post(f"{TELEGRAM_API_URL}/answerCallbackQuery", json={"callback_query_id": callback_id, "text": text})

def get_coordinates(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'PanditjiVedicBot/1.0'}
        res = requests.get(url, headers=headers, timeout=5).json()
        if res and len(res) > 0:
            return float(res[0]['lat']), float(res[0]['lon']), res[0].get('display_name', city_name).split(',')[0]
    except Exception:
        pass
    return 28.6139, 77.2090, city_name

def calculate_positions(day, month, year, hour, minute, lat, lon):
    swe.set_ephe_path(None)
    dt_ist = datetime(year, month, day, hour, minute)
    dt_utc = dt_ist - timedelta(hours=5, minutes=30)
    utc_decimal = dt_utc.hour + (dt_utc.minute / 60.0)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal)
    
    sun_calc = swe.calc_ut(jdut, swe.SUN)
    moon_calc = swe.calc_ut(jdut, swe.MOON)
    
    sun_lon = sun_calc[0] if isinstance(sun_calc[0], float) else sun_calc[0][0]
    moon_lon = moon_calc[0] if isinstance(moon_calc[0], float) else moon_calc[0][0]
    
    try:
        _, ascmc = swe.houses(jdut, lat, lon, b'W')
        asc_lon = ascmc[0]
    except Exception:
        asc_lon = 0.0
        
    return sun_lon, moon_lon, asc_lon

def build_menu_keyboard(asc_idx, sun_idx, moon_idx):
    """Embeds the calculated sign indices directly into the buttons to save processing time"""
    data_str = f"{asc_idx}|{sun_idx}|{moon_idx}"
    
    keyboard = [
        [
            {"text": "🎓 Education", "callback_data": f"cat:edu|{data_str}"},
            {"text": "💼 Career", "callback_data": f"cat:car|{data_str}"}
        ],
        [
            {"text": "💰 Finances", "callback_data": f"cat:fin|{data_str}"},
            {"text": "🏥 Health", "callback_data": f"cat:hea|{data_str}"}
        ],
        [
            {"text": "❤️ Relationships", "callback_data": f"cat:rel|{data_str}"},
            {"text": "💍 Marriage", "callback_data": f"cat:mar|{data_str}"}
        ],
        [
            {"text": "🏡 Family", "callback_data": f"cat:fam|{data_str}"},
            {"text": "✈️ Travel", "callback_data": f"cat:tra|{data_str}"}
        ],
        [
            {"text": "🏠 Property", "callback_data": f"cat:pro|{data_str}"},
            {"text": "🧘 Spiritual", "callback_data": f"cat:spi|{data_str}"}
        ],
        [
            {"text": "⚖️ Obstacles", "callback_data": f"cat:obs|{data_str}"},
            {"text": "👶 Children", "callback_data": f"cat:chi|{data_str}"}
        ],
        [
            {"text": "🧠 Mental Peace", "callback_data": f"cat:men|{data_str}"}
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

        # --- HANDLE INLINE BUTTON CLICKS (OPTIMIZED FOR SPEED) ---
        if "callback_query" in update:
            cb = update["callback_query"]
            chat_id = cb["message"]["chat"]["id"]
            data = cb["data"]
            answer_callback(cb["id"], "Consulting the stars...")

            try:
                # Instantly extract the pre-calculated signs from the button data
                parts = data.replace("cat:", "").split("|")
                cat_code = parts[0]
                asc_sign_name = ZODIAC_SIGNS[int(parts[1])]
                sun_sign_name = ZODIAC_SIGNS[int(parts[2])]
                moon_sign_name = ZODIAC_SIGNS[int(parts[3])]
                
                cat_name, cat_focus = CATEGORIES.get(cat_code, ("🔮 General", "General life guidance"))

                prompt = f"""
                You are Panditji, an expert Vedic Astrologer. Today's date is {today_date}.
                User requested a deep-dive reading for: **{cat_name}**.
                
                Core Placements: Ascendant ({asc_sign_name}), Sun ({sun_sign_name}), Moon ({moon_sign_name}).
                Astrological Focus: {cat_focus}
                
                Provide a structured response using these exactly 5 bold headings:
                1. **Planetary Influences**: Analyze their foundation.
                2. **Current Situation**: Intuitive insight into their life right now based on transits.
                3. **Short-Term Forecast**: Predictions for the next 3 to 6 months.
                4. **Long-Term Trajectory**: Outlook for the next 1 to 3 years.
                5. **Vedic Remedies (Upayas)**: 2 highly practical, safe, non-gemstone remedies.
                
                CRITICAL: Keep your response punchy, direct, and STRICTLY under 200 words total so the server does not timeout.
                """

                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                res = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
                
                if res.status_code == 200:
                    ai_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                    # Pass the indices back to keep the menu active
                    menu = build_menu_keyboard(int(parts[1]), int(parts[2]), int(parts[3]))
                    send_message(chat_id, ai_text, reply_markup=menu)
                else:
                    send_message(chat_id, "The stars are cloudy right now. Please try again.")

            except Exception as e:
                send_message(chat_id, f"Error processing selection: {str(e)}")

            return jsonify(status="success"), 200

        # --- HANDLE DIRECT TEXT MESSAGES (INITIAL CALCULATION) ---
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            if user_text.startswith("/start"):
                welcome_msg = "Welcome! Please send your birth details in this format:\nDD-MM-YYYY HH:MM City\n(e.g., 05-09-1981 12:16 Amritsar)"
                send_message(chat_id, welcome_msg)
            else:
                send_message(chat_id, "Locating coordinates, calculating Lagna, and drawing your natal chart...")

                try:
                    match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})\s+(.+)', user_text)
                    if not match:
                        send_message(chat_id, "Please use format: DD-MM-YYYY HH:MM City\n(e.g., 05-09-1981 12:16 Amritsar)")
                        return jsonify(status="success"), 200
                        
                    day, month, year, hour, minute, city_input = match.groups()
                    day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                    city_input = city_input.strip()

                    lat, lon, city_clean = get_coordinates(city_input)
                    sun_lon, moon_lon, asc_lon = calculate_positions(day, month, year, hour, minute, lat, lon)
                    
                    asc_sign_index = int(asc_lon / 30) % 12
                    sun_sign_index = int(sun_lon / 30) % 12
                    moon_sign_index = int(moon_lon / 30) % 12
                    
                    asc_sign_name = ZODIAC_SIGNS[asc_sign_index]
                    sun_sign_name = ZODIAC_SIGNS[sun_sign_index]
                    moon_sign_name = ZODIAC_SIGNS[moon_sign_index]
                    
                    north = chart.NorthChart("Natal Chart", f"{day:02d}-{month:02d}-{year} ({city_clean})", IsFullChart=False)
                    north.set_ascendantsign(asc_sign_name)
                    north.add_planet(chart.SUN, "Su", sun_sign_index + 1)
                    north.add_planet(chart.MOON, "Mo", moon_sign_index + 1)
                    
                    os.makedirs("/tmp", exist_ok=True)
                    svg_path = "/tmp/natal_chart.svg"
                    north.draw("/tmp/", "natal_chart")
                    send_document(chat_id, svg_path)

                    prompt = f"""
                    You are Panditji. Today's date is {today_date}.
                    Calculated Placements: Ascendant ({asc_sign_name}), Sun ({sun_sign_name}), Moon ({moon_sign_name}).
                    
                    Provide a concise general overview highlighting their {asc_sign_name} Lagna, Sun/Moon dynamic, and current major transits. 
                    Keep under 150 words. Invite them to pick a domain option below for a detailed 5-part analysis.
                    """

                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                    res = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
                    
                    # Pass the indices into the keyboard builder
                    menu = build_menu_keyboard(asc_sign_index, sun_sign_index, moon_sign_index)
                    
                    if res.status_code == 200:
                        ai_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                        send_message(chat_id, ai_text, reply_markup=menu)
                    else:
                        send_message(chat_id, "Select a category below to view your reading:", reply_markup=menu)

                except Exception as e:
                    send_message(chat_id, f"Technical Error: {str(e)}")
                
        return jsonify(status="success"), 200
