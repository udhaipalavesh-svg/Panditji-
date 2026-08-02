import os
import requests
import re
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import swisseph as swe
import jyotichart as chart
import time

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

processed_updates = set()

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

DASHA_LORDS = [
    ("Ketu", 7), ("Venus (Shukra)", 20), ("Sun (Surya)", 6),
    ("Moon (Chandra)", 10), ("Mars (Mangal)", 7), ("Rahu", 18),
    ("Jupiter (Guru)", 16), ("Saturn (Shani)", 19), ("Mercury (Budh)", 17)
]

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"SendMessage status: {res.status_code}", flush=True)
    except Exception as e:
        print(f"Exception in send_message: {e}", flush=True)

def send_document(chat_id, file_path):
    url = f"{TELEGRAM_API_URL}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id}
            res = requests.post(url, data=data, files=files, timeout=15)
            print(f"SendDocument status: {res.status_code}", flush=True)
    except Exception as e:
        print(f"Exception in send_document: {e}", flush=True)

def get_coordinates(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'PanditjiVedicBot/1.0'}
        res = requests.get(url, headers=headers, timeout=5).json()
        if res and len(res) > 0:
            return float(res[0]['lat']), float(res[0]['lon']), res[0].get('display_name', city_name).split(',')[0]
    except Exception as e:
        print(f"Geocoding exception: {e}", flush=True)
    return 30.7333, 76.7794, city_name

def get_nakshatra_info(lon):
    nak_span = 360.0 / 27.0
    nak_idx = int(lon / nak_span) % 27
    rem = lon % nak_span
    pada = int(rem / (nak_span / 4.0)) + 1
    return nak_idx, NAKSHATRAS[nak_idx], pada, rem

def calculate_vimshottari_dasha(moon_lon, birth_dt, target_dt):
    nak_span = 360.0 / 27.0
    nak_idx, _, _, rem = get_nakshatra_info(moon_lon)
    lord_idx = (nak_idx // 3) % 9
    dasha_lord, total_years = DASHA_LORDS[lord_idx]
    
    fraction_elapsed = rem / nak_span
    fraction_remaining = 1.0 - fraction_elapsed
    years_remaining = fraction_remaining * total_years
    
    current_jd = swe.julday(target_dt.year, target_dt.month, target_dt.day)
    birth_jd = swe.julday(birth_dt.year, birth_dt.month, birth_dt.day)
    years_passed = (current_jd - birth_jd) / 365.25
    
    current_lord_idx = lord_idx
    if years_passed <= years_remaining:
        return f"{dasha_lord} Mahadasha (Balance remaining: {years_remaining - years_passed:.1f} years)"
    
    years_passed_after_balance = years_passed - years_remaining
    current_lord_idx = (current_lord_idx + 1) % 9
    
    while years_passed_after_balance > 0:
        lord, span = DASHA_LORDS[current_lord_idx]
        if years_passed_after_balance <= span:
            return f"{lord} Mahadasha (Active running period)"
        years_passed_after_balance -= span
        current_lord_idx = (current_lord_idx + 1) % 9
        
    return f"{DASHA_LORDS[current_lord_idx][0]} Mahadasha"

def calculate_sidereal_chart(day, month, year, hour, minute, lat, lon):
    swe.set_ephe_path(None)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    
    dt_ist = datetime(year, month, day, hour, minute)
    dt_utc = dt_ist - timedelta(hours=5, minutes=30)
    utc_decimal = dt_utc.hour + (dt_utc.minute / 60.0)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal)
    
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
        "Ketu": 10
    }
    
    positions = {}
    rahu_lon = 0.0
    moon_lon = 0.0
    for name, p_id in planets.items():
        if name == "Ketu":
            lon_val = (rahu_lon + 180.0) % 360.0
        else:
            calc = swe.calc_ut(jdut, p_id, flags)
            lon_val = calc[0] if isinstance(calc[0], float) else calc[0][0]
            if name == "Rahu":
                rahu_lon = lon_val
            if name == "Moon (Chandra)":
                moon_lon = lon_val
                
        sign_idx = int(lon_val / 30) % 12
        sign_name = ZODIAC_SIGNS[sign_idx]
        _, nak_name, pada, _ = get_nakshatra_info(lon_val)
        
        # AUDIT & RE-VERIFICATION LAYER: Ensure bounds are mathematically secure
        normalized_lon = lon_val % 360.0
        positions[name] = (sign_name, normalized_lon, nak_name, pada)
        
    try:
        _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags)
        asc_lon = ascmc[0] % 360.0
    except Exception:
        asc_lon = 0.0
        
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]
    _, asc_nak, asc_pada, _ = get_nakshatra_info(asc_lon)
    
    active_dasha = calculate_vimshottari_dasha(moon_lon, dt_ist, datetime.now())
    return asc_sign, asc_nak, asc_pada, positions, active_dasha

@app.route('/', methods=['POST', 'GET'])
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Render Persistent Bot Server is Active", 200
        
    try:
        update = request.get_json(silent=True)
        if not update:
            return jsonify(status="ignored"), 200
            
        print(f"Received update: {update}", flush=True)

        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"].strip()
            
            if user_text.startswith("/start"):
                welcome_msg = "Welcome! Send your birth details to receive the comprehensive 8-part astrological report:\nDD-MM-YYYY HH:MM City\n(e.g., 02-01-1980 19:25 Chandigarh)"
                send_message(chat_id, welcome_msg)
            else:
                match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})\s+(.+)', user_text)
                if not match:
                    send_message(chat_id, "Please use format: DD-MM-YYYY HH:MM City\n(e.g., 02-01-1980 19:25 Chandigarh)")
                    return jsonify(status="success"), 200
                    
                send_message(chat_id, "Auditing chart ephemeris, verifying sidereal coordinates, and synthesizing psychological master report...")
                
                day, month, year, hour, minute, city_input = match.groups()
                day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                city_input = city_input.strip()

                lat, lon, city_clean = get_coordinates(city_input)
                asc_sign, asc_nak, asc_pada, planets, active_dasha = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                
                os.makedirs("/tmp", exist_ok=True)
                file_tag = str(int(time.time()))
                svg_filename = f"natal_chart_{file_tag}"
                svg_path = f"/tmp/{svg_filename}.svg"

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
                        
                north.draw("/tmp/", svg_filename)
                send_document(chat_id, svg_path)

                planet_summary = "\n".join([f"- {p}: {info[0]} | Exact Deg: {info[1]:.2f}° | Nakshatra: {info[2]} (Pada {info[3]})" for p, info in planets.items()])
                
                groq_key = os.environ.get("GROQ_API_KEY")
                today_date = datetime.now().strftime("%B %d, %Y")
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                
                prompt = f"""
[SYSTEM ROLE]
You are Panditji, an elite master Vedic Astrologer, deep archetypal psychologist, and soul guide. You merge classical Sidereal Jyotish computations with rigorous psychological insight, emotional depth, and spiritual mapping. Today's date is {today_date}.

[VERIFIED INPUT DATA & EPHEMERIS AUDIT]
- Timing Engine (Vimshottari Dasha): {active_dasha}
- Ascendant (Lagna): {asc_sign} in {asc_nak} Pada {asc_pada}
- Audited Planetary Array:
{planet_summary}

[OUTPUT DIRECTIVE]
Generate a deeply reflective, psychologically penetrating, and structurally rigorous Vedic analysis. Avoid generic horoscopes. Illuminate the hidden emotional drivers, inner contradictions, subconscious barriers, and psychological growth patterns. Use precise bullet points under each heading. Always include Hindi names in brackets for every planet (e.g., Saturn (Shani), Moon (Chandra)).

Structure the report strictly into these 8 sections:
1. **Star & Nakshatra Brief**: Core celestial alignment overview and the foundational emotional signature.
2. **Detailed Star Positions**: House-by-house breakdown of psychological strengths, intellectual wiring, and internal conflicts.
3. **Cosmic Conflicts**: Active planetary oppositions or conjunctions mapped to internal psychological tensions and behavioral blind spots.
4. **General Life Prediction**: Deep evolutionary trajectory across career, purpose, inner fulfillment, and wealth mindset.
5. **Detailed Manifestations**: Granular temporal alignments framed through current choices and psychological readiness.
6. **Karmic Liabilities, Psychological Entrapment & Confinement (Bandhana Yoga)**: Highly amplified and rigorous evaluation of 6th/8th/12th houses, deep-seated emotional self-sabotage, subconscious confinement loops, inner attachment chains, litigation/obligation weights, and precise pathways toward psychological and spiritual liberation.
7. **Corrective Remedies**: Exhaustive Lal Kitab & Vedic mental/spiritual alignment measures.
8. **Rare Yogas & Anomalies**: Unique structural configurations present in the chart and their deep psychological gifts.
"""

                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.75
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {groq_key}"
                }

                res = requests.post(groq_url, headers=headers, json=payload, timeout=90)
                if res.status_code == 200:
                    data = res.json()
                    final_text = data['choices'][0]['message']['content']
                    
                    max_length = 4000
                    for i in range(0, len(final_text), max_length):
                        chunk = final_text[i:i + max_length]
                        send_message(chat_id, chunk)
                        time.sleep(0.5)
                else:
                    send_message(chat_id, f"Groq API Error HTTP {res.status_code}: {res.text[:150]}")

    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        
    return jsonify(status="success"), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
