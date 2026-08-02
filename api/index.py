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

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

CATEGORIES = {
    "edu": ("🎓 Education", "4th & 5th houses, Mercury (Budh) and Jupiter (Guru)."),
    "car": ("💼 Career Stagnation / Layoffs", "10th, 6th & 11th houses, Saturn (Shani) and Sun (Surya)."),
    "fin": ("💰 Financial Disputes & Debt", "2nd, 6th & 11th houses, Mars (Mangal) and Rahu."),
    "hea": ("🏥 Medical Issues & Surgery", "1st, 6th & 8th houses, Sun (Surya) and Moon (Chandra)."),
    "rel": ("❤️ Relationships & Burnout", "5th & 7th houses, Venus (Shukra) and Moon (Chandra)."),
    "mar": ("💍 High-Conflict Marriage & Divorce", "7th & 9th houses, Venus (Shukra) and Saturn (Shani)."),
    "fam": ("🏡 Family Environment", "2nd & 4th houses, Moon (Chandra) and Jupiter (Guru)."),
    "tra": ("✈️ Foreign Travel & Visa Blocks", "9th & 12th houses, Rahu and Moon (Chandra)."),
    "pro": ("🏠 Property & Legal Disputes", "4th house, Mars (Mangal) and Saturn (Shani)."),
    "spi": ("🧘 Spiritual Growth & Karma", "8th, 9th & 12th houses, Ketu and Jupiter (Guru)."),
    "obs": ("⚖️ Legal Battles, Courts & Enemies", "6th & 8th houses, Saturn (Shani), Mars (Mangal), and Rahu."),
    "chi": ("👶 Children & Progeny Delays", "5th house, Jupiter (Guru) and Ketu."),
    "men": ("🧠 Mental Peace & Anxiety", "4th & 12th houses, Moon (Chandra) and Mercury (Budh).")
}

def send_message(chat_id, text, reply_markup=None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload)

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"{TELEGRAM_API_URL}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
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
    return 30.7333, 76.7794, city_name

def get_nakshatra_info(lon):
    nak_span = 360.0 / 27.0
    nak_idx = int(lon / nak_span) % 27
    rem = lon % nak_span
    pada = int(rem / (nak_span / 4.0)) + 1
    return NAKSHATRAS[nak_idx], pada

def calculate_sidereal_chart(day, month, year, hour, minute, lat, lon):
    swe.set_ephe_path(None)
    # Set Sidereal Mode to Lahiri (Chitra Paksha)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    
    dt_ist = datetime(year, month, day, hour, minute)
    dt_utc = dt_ist - timedelta(hours=5, minutes=30)
    utc_decimal = dt_utc.hour + (dt_utc.minute / 60.0)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal)
    
    # Use Sidereal calculation flags
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    
    planets = {
        "Sun (Surya)": swe.SUN,
        "Moon (Chandra)": swe.MOON,
        "Mars (Mangal)": swe.MARS,
        "Mercury (Budh)": swe.MERCURY,
        "Jupiter (Guru)": swe.JUPITER,
        "Venus (Shukra)": swe.VENUS,
        "Saturn (Shani)": swe.SATURN,
        "Rahu": swe.MEAN_NODE,
        "Ketu": 10  # Calculated dynamically or offset from Rahu
    }
    
    positions = {}
    rahu_lon = 0.0
    for name, p_id in planets.items():
        if name == "Ketu":
            lon_val = (rahu_lon + 180.0) % 360.0
        else:
            calc = swe.calc_ut(jdut, p_id, flags)
            lon_val = calc[0] if isinstance(calc[0], float) else calc[0][0]
            if name == "Rahu":
                rahu_lon = lon_val
                
        sign_idx = int(lon_val / 30) % 12
        sign_name = ZODIAC_SIGNS[sign_idx]
        nak_name, pada = get_nakshatra_info(lon_val)
        positions[name] = (sign_name, lon_val, nak_name, pada)
        
    try:
        _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags)
        asc_lon = ascmc[0]
    except Exception:
        asc_lon = 0.0
        
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]
    asc_nak, asc_pada = get_nakshatra_info(asc_lon)
    return asc_sign, asc_nak, asc_pada, positions

def build_menu_keyboard(city_clean, day, month, year, hour, minute):
    param_str = f"{day}-{month}-{year}-{hour}-{minute}-{city_clean}"
    keyboard = [
        [
            {"text": "🎓 Education", "callback_data": f"cat:edu|{param_str}"},
            {"text": "💼 Career/Layoffs", "callback_data": f"cat:car|{param_str}"}
        ],
        [
            {"text": "💰 Finances/Debt", "callback_data": f"cat:fin|{param_str}"},
            {"text": "🏥 Medical/Surgery", "callback_data": f"cat:hea|{param_str}"}
        ],
        [
            {"text": "❤️ Relationships", "callback_data": f"cat:rel|{param_str}"},
            {"text": "💍 Marriage/Divorce", "callback_data": f"cat:mar|{param_str}"}
        ],
        [
            {"text": "🏡 Family", "callback_data": f"cat:fam|{param_str}"},
            {"text": "✈️ Travel/Visas", "callback_data": f"cat:tra|{param_str}"}
        ],
        [
            {"text": "🏠 Property/Legal", "callback_data": f"cat:pro|{param_str}"},
            {"text": "🧘 Spiritual Path", "callback_data": f"cat:spi|{param_str}"}
        ],
        [
            {"text": "⚖️ Courts & Enemies", "callback_data": f"cat:obs|{param_str}"},
            {"text": "👶 Progeny Delays", "callback_data": f"cat:chi|{param_str}"}
        ],
        [
            {"text": "🧠 Mental Peace", "callback_data": f"cat:men|{param_str}"}
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

        if "callback_query" in update:
            cb = update["callback_query"]
            chat_id = cb["message"]["chat"]["id"]
            message_id = cb["message"]["message_id"]
            data = cb["data"]
            
            answer_callback(cb["id"])
            edit_message(chat_id, message_id, "Consulting Sidereal Sidhi & Nakshatras... ⏳")

            try:
                parts = data.replace("cat:", "").split("|")
                cat_code = parts[0]
                d_parts = parts[1].split("-")
                day, month, year, hour, minute = map(int, d_parts[:5])
                city_input = d_parts[5]
                
                cat_name, cat_focus = CATEGORIES.get(cat_code, ("🔮 General", "General life guidance"))
                lat, lon, city_clean = get_coordinates(city_input)
                asc_sign, asc_nak, asc_pada, planets = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                
                planet_summary = "\n".join([f"- {p}: {info[0]} | Nakshatra: {info[2]} (Pada {info[3]})" for p, info in planets.items()])

                prompt = f"""
                You are Panditji, an expert Vedic Astrologer using precise Sidereal Lahiri calculations. Today's date is {today_date}.
                Domain: **{cat_name}** ({cat_focus})
                
                Precise Sidereal Chart Data:
                - Ascendant (Lagna): {asc_sign} in {asc_nak} Pada {asc_pada}
                {planet_summary}
                
                RULE: Mention Hindi names in brackets for every planet (e.g., Saturn (Shani), Moon (Chandra)).
                
                Structure response into these 5 strict headings:
                1. **Planetary & Nakshatra Influences**: Analyze how these specific house lords, planetary placements, and Nakshatra energies impact this domain.
                2. **Current Situation**: Real-time transit analysis.
                3. **Short-Term Forecast**: Next 3-6 months.
                4. **Long-Term Trajectory**: 1-3 years outlook.
                5. **Lal Kitab & Vedic Remedies**: 2 practical, safe, non-gemstone remedies (e.g., specific charity, animal feeding, or water offerings).
                
                Keep it structured, punchy, and concise.
                """

                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                res = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
                
                if res.status_code == 200:
                    ai_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                    menu = build_menu_keyboard(city_clean, day, month, year, hour, minute)
                    send_message(chat_id, ai_text, reply_markup=menu)
                else:
                    send_message(chat_id, "The connection flickered. Please try clicking the button again.")

            except Exception as e:
                send_message(chat_id, f"Error: {str(e)}")

            return jsonify(status="success"), 200

        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            if user_text.startswith("/start"):
                welcome_msg = "Welcome! Please send your birth details in this format:\nDD-MM-YYYY HH:MM City\n(e.g., 01-01-1900 12:00 Amritsar)"
                send_message(chat_id, welcome_msg)
            else:
                send_message(chat_id, "Calculating Sidereal Lahiri chart, Nakshatras, and drawing chart...")

                try:
                    match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})\s+(.+)', user_text)
                    if not match:
                        send_message(chat_id, "Please use format: DD-MM-YYYY HH:MM City\n(e.g., 01-01-1900 12:00 Amritsar)")
                        return jsonify(status="success"), 200
                        
                    day, month, year, hour, minute, city_input = match.groups()
                    day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                    city_input = city_input.strip()

                    lat, lon, city_clean = get_coordinates(city_input)
                    asc_sign, asc_nak, asc_pada, planets = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                    
                    north = chart.NorthChart("Natal Chart (Lahiri)", f"{day:02d}-{month:02d}-{year} ({city_clean})", IsFullChart=True)
                    north.set_ascendantsign(asc_sign)
                    
                    p_map = {
                        "Sun (Surya)": chart.SUN, "Moon (Chandra)": chart.MOON,
                        "Mars (Mangal)": chart.MARS, "Mercury (Budh)": chart.MERCURY,
                        "Jupiter (Guru)": chart.JUPITER, "Venus (Shukra)": chart.VENUS,
                        "Saturn (Shani)": chart.SATURN, "Rahu": chart.RAHU, "Ketu": chart.KETU
                    }
                    for p_name, p_code in p_map.items():
                        if p_name in planets:
                            sign_name, _, _, _ = planets[p_name]
                            sign_idx = ZODIAC_SIGNS.index(sign_name) + 1
                            north.add_planet(p_code, p_name[:2], sign_idx)
                            
                    os.makedirs("/tmp", exist_ok=True)
                    svg_path = "/tmp/natal_chart.svg"
                    north.draw("/tmp/", "natal_chart")
                    send_document(chat_id, svg_path)

                    planet_summary = "\n".join([f"- {p}: {info[0]} | {info[2]} (Pada {info[3]})" for p, info in planets.items()])
                    prompt = f"""
                    You are Panditji. Today's date is {today_date}.
                    Sidereal Chart Data: Ascendant ({asc_sign} in {asc_nak} Pada {asc_pada}), Placements:\n{planet_summary}
                    
                    RULE: Mention Hindi names in brackets for any planet.
                    Provide a concise general overview highlighting their Ascendant and Nakshatra core dynamic. Keep under 150 words.
                    """

                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                    res = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
                    
                    menu = build_menu_keyboard(city_clean, day, month, year, hour, minute)
                    
                    if res.status_code == 200:
                        ai_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                        send_message(chat_id, ai_text, reply_markup=menu)
                    else:
                        send_message(chat_id, "Select a category below:", reply_markup=menu)

                except Exception as e:
                    send_message(chat_id, f"Technical Error: {str(e)}")
                
        return jsonify(status="success"), 200
        
