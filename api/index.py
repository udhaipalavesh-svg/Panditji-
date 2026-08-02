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

# Vimshottari Dasha Lords and their span in years
DASHA_LORDS = [
    ("Ketu", 7), ("Venus (Shukra)", 20), ("Sun (Surya)", 6),
    ("Moon (Chandra)", 10), ("Mars (Mangal)", 7), ("Rahu", 18),
    ("Jupiter (Guru)", 16), ("Saturn (Shani)", 19), ("Mercury (Budh)", 17)
]
TOTAL_DASHA_YEARS = 120

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def send_document(chat_id, file_path):
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': chat_id}
        requests.post(f"{TELEGRAM_API_URL}/sendDocument", data=data, files=files)

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
    return nak_idx, NAKSHATRAS[nak_idx], pada, rem

def calculate_vimshottari_dasha(moon_lon, birth_dt, target_dt):
    """Calculates active Mahadasha based on Moon's Sidereal Nakshatra position"""
    nak_span = 360.0 / 27.0
    nak_idx, nak_name, _, rem = get_nakshatra_info(moon_lon)
    
    # Each Nakshatra spans 13.3333 degrees (800 minutes). Ruler sequence maps every 3 nakshatras to a planet lord.
    lord_idx = (nak_idx // 3) % 9
    dasha_lord, total_years = DASHA_LORDS[lord_idx]
    
    # Fraction of dasha elapsed based on how far into the nakshatra the moon is
    fraction_elapsed = rem / nak_span
    fraction_remaining = 1.0 - fraction_elapsed
    years_remaining = fraction_remaining * total_years
    
    # Calculate birth JD to target JD progression
    current_jd = swe.julday(target_dt.year, target_dt.month, target_dt.day)
    birth_jd = swe.julday(birth_dt.year, birth_dt.month, birth_dt.day)
    days_passed = current_jd - birth_jd
    years_passed = days_passed / 365.25
    
    # Traverse through subsequent dashas to find current active Mahadasha
    accumulated_years = years_remaining
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
        positions[name] = (sign_name, lon_val, nak_name, pada)
        
    try:
        _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags)
        asc_lon = ascmc[0]
    except Exception:
        asc_lon = 0.0
        
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]
    _, asc_nak, asc_pada, _ = get_nakshatra_info(asc_lon)
    
    active_dasha = calculate_vimshottari_dasha(moon_lon, dt_ist, datetime.now())
    return asc_sign, asc_nak, asc_pada, positions, active_dasha

@app.route('/api', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Vercel Webhook is Active", 200
        
    if request.method == 'POST':
        update = request.get_json()
        gemini_key = os.environ.get("GEMINI_API_KEY")
        today_date = datetime.now().strftime("%B %d, %Y")

        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            if user_text.startswith("/start"):
                welcome_msg = "Welcome! Send your birth details to receive the audited, deep 8-part astrological report:\nDD-MM-YYYY HH:MM City\n(e.g., 02-01-1980 19:25 Chandigarh)"
                send_message(chat_id, welcome_msg)
            else:
                send_message(chat_id, "Executing dual-engine Sidereal scan, computing Dasha timelines and auditing planetary conflicts...")

                try:
                    match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})\s+(.+)', user_text)
                    if not match:
                        send_message(chat_id, "Please use format: DD-MM-YYYY HH:MM City\n(e.g., 02-01-1980 19:25 Chandigarh)")
                        return jsonify(status="success"), 200
                        
                    day, month, year, hour, minute, city_input = match.groups()
                    day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                    city_input = city_input.strip()

                    lat, lon, city_clean = get_coordinates(city_input)
                    asc_sign, asc_nak, asc_pada, planets, active_dasha = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                    
                    # Generate Chart SVG
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

                    planet_summary = "\n".join([f"- {p}: {info[0]} | Nakshatra: {info[2]} (Pada {info[3]})" for p, info in planets.items()])
                    
                    # STEP 1: Generator Prompt
                    gen_prompt = f"""
                    You are Panditji, a master Vedic Astrologer. Today's date is {today_date}.
                    Active Timing Engine (Vimshottari Dasha): {active_dasha}
                    
                    Sidereal Lahiri Chart Data:
                    - Ascendant (Lagna): {asc_sign} in {asc_nak} Pada {asc_pada}
                    {planet_summary}
                    
                    Write an exhaustive, uncompromising 8-part analytical report covering:
                    1. Star and Nakshatra Position in Brief
                    2. Star and Nakshatra Positions in Detail
                    3. Conflicts Amongst Stars and Nakshatras
                    4. General Prediction
                    5. Prediction in Detail
                    6. Potential Issues, Psychological Impact, and Legal/Confinement Deductions (explicitly analyze Bandhana Yoga, 6th/8th/12th house weights, and prison/litigation reality if present)
                    7. Remedies (Exhaustive Lal Kitab & Vedic Corrective Actions)
                    8. Extraordinary Cosmic Anomalies & Rare Yogas
                    
                    RULE: Mention Hindi names in brackets for every planet.
                    """

                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                    res1 = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": gen_prompt}]}]})
                    
                    if res1.status_code == 200:
                        initial_report = res1.json()['candidates'][0]['content']['parts'][0]['text']
                        
                        # STEP 2: Adversarial Reflection / Auditor Prompt
                        audit_prompt = f"""
                        You are a strict, skeptical Senior Master Jyotishi and Quality Control Auditor. Review the following astrological report generated for a chart with Ascendant {asc_sign} and Active Dasha {active_dasha}.
                        
                        Draft Report to Audit:
                        {initial_report}
                        
                        Your Task:
                        - Audit the report for absolute technical accuracy, correct house lord associations, Nakshatra consistency, and depth.
                        - Ensure all 8 structured headings are fully fleshed out.
                        - Correct any logical flaws or surface-level summaries, making the analysis intensely sharp, accurate, and psychological.
                        - Return the final, polished, airtight 8-part report.
                        """
                        
                        res2 = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": audit_prompt}]}]})
                        
                        if res2.status_code == 200:
                            final_text = res2.json()['candidates'][0]['content']['parts'][0]['text']
                            send_message(chat_id, final_text)
                        else:
                            send_message(chat_id, initial_report)
                    else:
                        send_message(chat_id, "The celestial connection flickered. Please resend your birth details.")

                except Exception as e:
                    send_message(chat_id, f"Technical Error: {str(e)}")
                
        return jsonify(status="success"), 200
        
