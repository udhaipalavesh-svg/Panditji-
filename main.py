import os
import requests
import re
import time
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import swisseph as swe
import jyotichart as chart

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from xml.sax.saxutils import escape

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

USER_SESSIONS = {}

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

HINDI_SIGNS = {
    "Aries": "Aries (Mesha)", "Taurus": "Taurus (Vrishabha)", "Gemini": "Gemini (Mithuna)",
    "Cancer": "Cancer (Karka)", "Leo": "Leo (Simha)", "Virgo": "Virgo (Kanya)",
    "Libra": "Libra (Tula)", "Scorpio": "Scorpio (Vrishchika)", "Sagittarius": "Sagittarius (Dhanu)",
    "Capricorn": "Capricorn (Makara)", "Aquarius": "Aquarius (Kumbha)", "Pisces": "Pisces (Meena)"
}

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

EXALTATION = {
    "Sun (Surya)": "Aries", "Moon (Chandra)": "Taurus", "Mars (Mangal)": "Capricorn",
    "Mercury (Budh)": "Virgo", "Jupiter (Guru)": "Cancer", "Venus (Shukra)": "Pisces",
    "Saturn (Shani)": "Libra", "Rahu": "Taurus", "Ketu": "Scorpio"
}
DEBILITATION = {
    "Sun (Surya)": "Libra", "Moon (Chandra)": "Scorpio", "Mars (Mangal)": "Cancer",
    "Mercury (Budh)": "Pisces", "Jupiter (Guru)": "Capricorn", "Venus (Shukra)": "Virgo",
    "Saturn (Shani)": "Aries", "Rahu": "Scorpio", "Ketu": "Taurus"
}
OWN_SIGNS = {
    "Sun (Surya)": ["Leo"], "Moon (Chandra)": ["Cancer"], "Mars (Mangal)": ["Aries", "Scorpio"],
    "Mercury (Budh)": ["Gemini", "Virgo"], "Jupiter (Guru)": ["Sagittarius", "Pisces"],
    "Venus (Shukra)": ["Taurus", "Libra"], "Saturn (Shani)": ["Capricorn", "Aquarius"]
}
COMBUSTION_ORB = {
    "Moon (Chandra)": 12, "Mars (Mangal)": 17, "Mercury (Budh)": 14,
    "Jupiter (Guru)": 11, "Venus (Shukra)": 10, "Saturn (Shani)": 15
}
MALEFICS = ["Saturn (Shani)", "Mars (Mangal)", "Rahu", "Ketu", "Sun (Surya)"]

DOSHA_MAP = {
    "Aries": "Pitta", "Taurus": "Kapha", "Gemini": "Vata", "Cancer": "Kapha",
    "Leo": "Pitta", "Virgo": "Vata", "Libra": "Vata", "Scorpio": "Kapha",
    "Sagittarius": "Pitta", "Capricorn": "Vata", "Aquarius": "Vata", "Pisces": "Kapha"
}

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    def attempt_send(parse_mode=None):
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode: 
            payload["parse_mode"] = parse_mode
        try:
            res = requests.post(url, json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            print(f"Exception in send_message: {e}", flush=True)
            return False

    if not attempt_send("Markdown"):
        attempt_send(None)

def send_document(chat_id, file_path):
    url = f"{TELEGRAM_API_URL}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': chat_id}
            res = requests.post(url, data=data, files=files, timeout=30)
            return res.status_code == 200
    except Exception as e:
        print(f"Exception in send_document: {e}", flush=True)
        return False

def generate_svg_chart(filename, title, asc_sign, planets_data):
    p_chart_map = {
        "Sun (Surya)": chart.SUN, "Moon (Chandra)": chart.MOON, "Mars (Mangal)": chart.MARS,
        "Mercury (Budh)": chart.MERCURY, "Jupiter (Guru)": chart.JUPITER, "Venus (Shukra)": chart.VENUS,
        "Saturn (Shani)": chart.SATURN, "Rahu": chart.RAHU, "Ketu": chart.KETU
    }
    svg_path = f"/tmp/{filename}.svg"
    north = chart.NorthChart(title, "", IsFullChart=True)
    north.set_ascendantsign(asc_sign)
    for p_name, p_data in planets_data.items():
        if p_name in p_chart_map:
            sign_name = p_data["sign"]
            north.add_planet(p_chart_map[p_name], p_name[:2], ZODIAC_SIGNS.index(sign_name) + 1)
    north.draw("/tmp/", filename)
    return svg_path

def generate_master_pdf(report_text, pdf_path, birth_details_str):
    try:
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=8, textColor=colors.HexColor('#4A154B'), alignment=TA_CENTER)
        heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=12, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#1D1C1D'))
        body_style = ParagraphStyle('ReportBody', parent=styles['Normal'], fontSize=9.5, leading=14, spaceAfter=6, alignment=TA_JUSTIFY)

        story = []
        story.append(Paragraph("<b>Panditji - Forensic Astrological Audit</b>", title_style))
        story.append(Paragraph(f"<b>Client Profile:</b> {escape(birth_details_str)}", body_style))
        story.append(Spacer(1, 12))

        for line in report_text.split('\n'):
            line = line.strip()
            if not line: 
                continue
            
            safe_line = escape(line)
            safe_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_line)
            safe_line = re.sub(r'^[\*\-]\s+', '• ', safe_line)
            
            if safe_line.startswith("# PART 1") or safe_line.startswith("# PART 2"):
                story.append(PageBreak())
                story.append(Paragraph(safe_line.replace("# ", ""), heading_style))
            elif re.match(r'^\d+\.\s+<b>', safe_line) or safe_line.startswith("# "):
                story.append(Spacer(1, 6))
                story.append(Paragraph(safe_line.replace("# ", ""), heading_style))
            else:
                story.append(Paragraph(safe_line, body_style))

        doc.build(story)
        return True
    except Exception as e:
        print(f"PDF GENERATION ERROR: {e}", flush=True)
        return False

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
    
    fraction_remaining = 1.0 - (rem / nak_span)
    years_remaining = fraction_remaining * total_years
    
    current_jd = swe.julday(target_dt.year, target_dt.month, target_dt.day)
    birth_jd = swe.julday(birth_dt.year, birth_dt.month, birth_dt.day)
    years_passed = (current_jd - birth_jd) / 365.25
    
    current_lord_idx = lord_idx
    if years_passed <= years_remaining:
        return f"{dasha_lord} Mahadasha (Balance: {years_remaining - years_passed:.1f}y)"
    
    years_passed_after_balance = years_passed - years_remaining
    current_lord_idx = (current_lord_idx + 1) % 9
    
    while years_passed_after_balance > 0:
        lord, span = DASHA_LORDS[current_lord_idx]
        if years_passed_after_balance <= span:
            return f"{lord} Mahadasha (Active)"
        years_passed_after_balance -= span
        current_lord_idx = (current_lord_idx + 1) % 9
        
    return f"{DASHA_LORDS[current_lord_idx][0]} Mahadasha"

def get_planet_dignity(planet, sign):
    if EXALTATION.get(planet) == sign: 
        return "Exalted (Uchcha) - Planet is at maximum strength"
    if DEBILITATION.get(planet) == sign: 
        return "Debilitated (Neecha) - Planet is severely weakened"
    if planet in OWN_SIGNS and sign in OWN_SIGNS[planet]: 
        return "Own Sign (Swavritti) - Planet is strong and comfortable"
    return "Neutral"

def get_aspects(planet, house):
    aspects = [7]
    if planet == "Mars (Mangal)": 
        aspects.extend([4, 8])
    elif planet == "Jupiter (Guru)": 
        aspects.extend([5, 9])
    elif planet == "Saturn (Shani)": 
        aspects.extend([3, 10])
    elif planet in ["Rahu", "Ketu"]: 
        aspects.extend([5, 9])
    return [((house - 1 + a) % 12) + 1 for a in aspects]

def get_house_of_planet(houses, planet_name):
    for h_num, h_data in houses.items():
        if planet_name in h_data["occupants"]:
            return h_num
    return None

def calculate_chart_logic(asc_sign, planets_full, birth_dt):
    now = datetime.now()
    age = (now - birth_dt).days // 365
    
    if age < 18:
        life_stage = f"CHILD (Age {age}): STRICTLY focus on House 4 (Home), House 5 (Education), House 9 (Mentorship). NO career/marriage predictions."
    elif 18 <= age <= 25:
        life_stage = f"YOUNG ADULT (Age {age}): Focus on House 9 (Higher Ed), House 10 (Early Career), House 1 (Identity). No marriage timelines yet."
    elif 26 <= age <= 40:
        life_stage = f"ESTABLISHMENT (Age {age}): Deep dive into House 10 (Career), House 7 (Marriage), House 2 (Wealth), House 6 (Disease/Debt)."
    elif 41 <= age <= 60:
        life_stage = f"CONSOLIDATION (Age {age}): Focus on House 11 (Gains), House 2 (Savings), House 8 (Longevity), House 10 (Authority). Address mid-life crises."
    else:
        life_stage = f"ELDER (Age {age}): STRICTLY focus on House 9 (Spirituality), House 12 (Moksha), House 8 (Pension), House 4 (Peace). NO aggressive career growth."

    sign_lords = {
        "Aries": "Mars (Mangal)", "Taurus": "Venus (Shukra)", "Gemini": "Mercury (Budh)",
        "Cancer": "Moon (Chandra)", "Leo": "Sun (Surya)", "Virgo": "Mercury (Budh)",
        "Libra": "Venus (Shukra)", "Scorpio": "Mars (Mangal)", "Sagittarius": "Jupiter (Guru)",
        "Capricorn": "Saturn (Shani)", "Aquarius": "Saturn (Shani)", "Pisces": "Jupiter (Guru)"
    }
    
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    houses = {}
    for i in range(12):
        house_num = i + 1
        sign = ZODIAC_SIGNS[(asc_idx + i) % 12]
        houses[house_num] = {"sign": sign, "hindi_sign": HINDI_SIGNS[sign], "ruler": sign_lords.get(sign, ""), "occupants": [], "aspected_by": []}
        
    for p_name, p_data in planets_full.items():
        for h_num, h_data in houses.items():
            if h_data["sign"] == p_data["sign"]:
                h_data["occupants"].append(p_name)
                break
                
    for p_name, p_data in planets_full.items():
        occ_house = get_house_of_planet(houses, p_name)
        if occ_house:
            for ah in get_aspects(p_name, occ_house):
                houses[ah]["aspected_by"].append(p_name)

    for h_num, h_data in houses.items():
        ruler = h_data["ruler"]
        h_data["ruler_placed_in"] = get_house_of_planet(houses, ruler) if ruler else None

    logic_summary = f"[LIFE STAGE FILTER - MANDATORY]: {life_stage}\n[PROGRAMMATIC HOUSE MAP]:\n"
    for h, data in houses.items():
        logic_summary += f"  House {h} ({data['hindi_sign']}, Ruled by {data['ruler']} in H{data['ruler_placed_in']}): Occ: {data['occupants'] if data['occupants'] else 'Empty'}. Asp: {data['aspected_by'] if data['aspected_by'] else 'None'}.\n"
    
    asc_dosha = DOSHA_MAP.get(asc_sign, "Unknown")
    moon_dosha = DOSHA_MAP.get(planets_full["Moon (Chandra)"]["sign"], "Unknown")
    psych_triggers = []
    
    moon_house = get_house_of_planet(houses, "Moon (Chandra)")
    mercury_house = get_house_of_planet(houses, "Mercury (Budh)")
    
    if moon_house in [6, 8, 12]: 
        psych_triggers.append("Moon in Dusthana indicates emotional volatility.")
    if planets_full["Moon (Chandra)"]["dignity"].startswith("Debilitated"): 
        psych_triggers.append("Debilitated Moon indicates depressive loops.")
    if mercury_house in [8, 12]: 
        psych_triggers.append("Mercury in 8th/12th creates nervous burnout.")

    threats = []
    opportunities = []
    
    h2_occ = houses[2]["occupants"] + houses[2]["aspected_by"]
    h4_occ = houses[4]["occupants"] + houses[4]["aspected_by"]
    h5_occ = houses[5]["occupants"] + houses[5]["aspected_by"]
    h6_occ = houses[6]["occupants"] + houses[6]["aspected_by"]
    h7_occ = houses[7]["occupants"] + houses[7]["aspected_by"]
    h8_occ = houses[8]["occupants"] + houses[8]["aspected_by"]
    h9_occ = houses[9]["occupants"] + houses[9]["aspected_by"]
    h10_occ = houses[10]["occupants"] + houses[10]["aspected_by"]
    h11_occ = houses[11]["occupants"] + houses[11]["aspected_by"]
    h12_occ = houses[12]["occupants"] + houses[12]["aspected_by"]

    if any(m in h8_occ for m in MALEFICS): 
        threats.append("Vector: HOSPITALIZATION | Trigger: Malefics in 8th House | Meaning: Risk of sudden trauma/surgery.")
    if houses[10]["ruler_placed_in"] in [8, 12]: 
        threats.append("Vector: CAREER TERMINATION | Trigger: 10th Lord in 8th/12th House | Meaning: Sudden job loss or business collapse.")
    if houses[2]["ruler_placed_in"] == 12 and "Rahu" in houses[2]["occupants"]: 
        threats.append("Vector: BANKRUPTCY | Trigger: 2nd Lord in 12th with Rahu | Meaning: Catastrophic wealth erosion.")
    if houses[7]["ruler_placed_in"] == 6 or any(m in h7_occ for m in ["Mars (Mangal)", "Rahu"]): 
        threats.append("Vector: DIVORCE | Trigger: 7th Lord in 6th or afflicted by Mars/Rahu | Meaning: High-conflict separation.")
    if "Rahu" in h6_occ or "Rahu" in h8_occ: 
        threats.append("Vector: LITIGATION/IMPRISONMENT | Trigger: Rahu in 6th/8th axis | Meaning: Entrapment in legal cases.")
    if "Venus (Shukra)" in h12_occ and "Rahu" in h12_occ: 
        threats.append("Vector: EXTRA-MARITAL | Trigger: Venus+Rahu in 12th | Meaning: Risk of clandestine affairs.")
    if houses[5]["ruler_placed_in"] in [6, 8, 12]: 
        threats.append("Vector: PROGENY ISSUES | Trigger: 5th Lord in 6th/8th/12th | Meaning: Delays or complications regarding children.")
    if houses[4]["ruler_placed_in"] in [6, 8, 12]: 
        threats.append("Vector: PROPERTY DISPUTES | Trigger: 4th Lord in 6th/8th/12th | Meaning: Litigation over real estate.")

    if "Jupiter (Guru)" in h10_occ or "Jupiter (Guru)" in h11_occ or houses[10]["ruler_placed_in"] == 11: 
        opportunities.append("Vector: PROMOTION | Trigger: Jupiter aspecting 10th/11th | Meaning: Leadership elevation.")
    if houses[2]["ruler_placed_in"] == 11 or houses[11]["ruler_placed_in"] == 2: 
        opportunities.append("Vector: DHANA YOGA | Trigger: 2nd/11th Lord exchange | Meaning: Massive wealth accumulation.")
    if "Jupiter (Guru)" in h8_occ or houses[8]["ruler_placed_in"] in [1, 5, 9, 11]: 
        opportunities.append("Vector: SUDDEN WEALTH | Trigger: 8th Lord well-placed | Meaning: Sudden unearned wealth/inheritance.")
    if houses[12]["ruler_placed_in"] in [1, 9, 10] or "Rahu" in h9_occ: 
        opportunities.append("Vector: FOREIGN SETTLEMENT | Trigger: 12th/9th Lord connection | Meaning: Success in foreign lands.")

    logic_summary += f"\n[AYURVEDIC BASELINE]: Ascendant is {asc_dosha}, Moon is {moon_dosha}.\n"
    logic_summary += f"[PSYCHOLOGICAL TRIGGERS]: {' '.join(psych_triggers) if psych_triggers else 'Baseline.'}\n"
    logic_summary += f"[ACTIVATED THREAT VECTORS]:\n - " + "\n - ".join(threats) if threats else "\n[ACTIVATED THREAT VECTORS]: None."
    logic_summary += f"\n[ACTIVATED OPPORTUNITY VECTORS]:\n - " + "\n - ".join(opportunities) if opportunities else "\n[ACTIVATED OPPORTUNITY VECTORS]: None."
        
    return logic_summary, age

def calculate_sidereal_chart(day, month, year, hour, minute, lat, lon):
    swe.set_ephe_path(None)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    
    dt_ist = datetime(year, month, day, hour, minute)
    dt_utc = dt_ist - timedelta(hours=5, minutes=30)
    utc_decimal = dt_utc.hour + (dt_utc.minute / 60.0)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal)
    
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    
    planets = {
        "Sun (Surya)": swe.SUN, "Moon (Chandra)": swe.MOON, "Mars (Mangal)": swe.MARS,
        "Mercury (Budh)": swe.MERCURY, "Jupiter (Guru)": swe.JUPITER, "Venus (Shukra)": swe.VENUS,
        "Saturn (Shani)": swe.SATURN, "Rahu": swe.MEAN_NODE, "Ketu": 10
    }
    
    positions = {}
    d9_positions = {}
    rahu_lon = 0.0
    moon_lon = 0.0
    sun_lon = 0.0
    
    for name, p_id in planets.items():
        if name == "Ketu":
            lon_val = (rahu_lon + 180.0) % 360.0
            speed = 0
        else:
            calc = swe.calc_ut(jdut, p_id, flags)
            if isinstance(calc, tuple):
                if isinstance(calc[0], float):
                    lon_val = calc[0]
                    speed = calc[3] if len(calc) > 3 else 0.0
                elif isinstance(calc[0], tuple) and len(calc[0]) > 3:
                    lon_val = calc[0][0]
                    speed = calc[0][3]
                else:
                    lon_val = calc[0][0]
                    speed = 0.0
            else:
                lon_val = 0.0
                speed = 0.0

            if name == "Rahu": rahu_lon = lon_val
            if name == "Moon (Chandra)": moon_lon = lon_val
            if name == "Sun (Surya)": sun_lon = lon_val
                
        sign_idx = int(lon_val / 30) % 12
        sign_name = ZODIAC_SIGNS[sign_idx]
        _, nak_name, pada, _ = get_nakshatra_info(lon_val)
        
        dignity = get_planet_dignity(name, sign_name)
        is_retro = speed < 0 if name not in ["Sun (Surya)", "Moon (Chandra)"] else False
        is_combust = False
        
        if name in COMBUSTION_ORB:
            dist_to_sun = abs(lon_val - sun_lon)
            if dist_to_sun > 180: 
                dist_to_sun = 360 - dist_to_sun
            if dist_to_sun < COMBUSTION_ORB[name]: 
                is_combust = True
                
        positions[name] = {
            "sign": sign_name, "hindi_sign": HINDI_SIGNS[sign_name], "lon": lon_val % 360.0, 
            "nak": nak_name, "pada": pada, "dignity": dignity, "retro": is_retro, "combust": is_combust
        }
        
        d9_sign_idx = int((lon_val % (30/9)) / (30/9)) + (sign_idx * 9)
        d9_sign_name = ZODIAC_SIGNS[d9_sign_idx % 12]
        d9_positions[name] = {"sign": d9_sign_name, "hindi_sign": HINDI_SIGNS[d9_sign_name]}
        
    try:
        _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags)
        asc_lon = ascmc[0] % 360.0
    except Exception:
        asc_lon = 0.0
        
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]
    _, asc_nak, asc_pada, _ = get_nakshatra_info(asc_lon)
    
    # Calculate D9 Ascendant
    asc_d9_sign_idx = int((asc_lon % (30/9)) / (30/9)) + (ZODIAC_SIGNS.index(asc_sign) * 9)
    asc_d9_sign = ZODIAC_SIGNS[asc_d9_sign_idx % 12]
    
    now_dt = datetime.now()
    active_dasha = calculate_vimshottari_dasha(moon_lon, dt_ist, now_dt)
    
    t_ctx = {
        "current_date": now_dt.strftime("%B %d, %Y"),
        "dasha_now": active_dasha,
        "dasha_5y": calculate_vimshottari_dasha(moon_lon, dt_ist, now_dt + timedelta(days=365 * 5))
    }
    
    logic_breakdown, age = calculate_chart_logic(asc_sign, positions, dt_ist)
    return asc_sign, asc_nak, asc_pada, positions, d9_positions, asc_d9_sign, t_ctx, logic_breakdown, age

@app.route('/', methods=['POST', 'GET'])
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Render Persistent Bot Server is Active", 200
        
    try:
        update = request.get_json(silent=True)
        if not update: 
            return jsonify(status="ignored"), 200
            
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"].strip()
            
            groq_key = os.environ.get("GROQ_API_KEY")
            groq_url = "https://api.groq.com/openai/v1/chat/completions"
            
            if user_text.startswith("/start"):
                if chat_id in USER_SESSIONS: 
                    del USER_SESSIONS[chat_id]
                welcome_msg = "Welcome! Send your birth details to receive your **Forensic Astrological Report**:\n`DD-MM-YYYY HH:MM City`\n(e.g., `05-09-1981 12:16 Amritsar`)"
                send_message(chat_id, welcome_msg)
                return jsonify(status="success"), 200
                
            # More forgiving regex (allows spaces around hyphens)
            match = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{4})\s+(\d{1,2}):(\d{1,2})\s+(.+)', user_text)
            
            if match:
                send_message(chat_id, "⏳ Calculating exact astronomical degrees, Ayurvedic doshas, and activated vectors...")
                
                day, month, year, hour, minute, city_input = match.groups()
                day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                city_input = city_input.strip()

                lat, lon, city_clean = get_coordinates(city_input)
                asc_sign, asc_nak, asc_pada, planets, d9_planets, asc_d9_sign, t_ctx, logic_breakdown, age = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                
                planet_summary = "\n".join([f"- {p}: {d['hindi_sign']} | Nak: {d['nak']} (P{d['pada']}) | Dignity: {d['dignity']} {'[Retrograde]' if d['retro'] else ''} {'[Combust]' if d['combust'] else ''}" for p, d in planets.items()])
                
                USER_SESSIONS[chat_id] = {
                    "asc_sign": asc_sign, "planet_summary": planet_summary, "t_ctx": t_ctx, 
                    "logic_breakdown": logic_breakdown, "age": age
                }
                
                os.makedirs("/tmp", exist_ok=True)
                file_tag = str(int(time.time()))
                
                # 1. Generate & Send Charts as separate SVGs
                d1_svg = generate_svg_chart(f"d1_{file_tag}", "Rasi (D1)", asc_sign, planets)
                d9_svg = generate_svg_chart(f"d9_{file_tag}", "Navamsha (D9)", asc_d9_sign, d9_planets)
                
                send_document(chat_id, d1_svg)
                send_document(chat_id, d9_svg)

                # 2. The Unified Master Output Prompt (Enforced)
                system_msg = """
You are Panditji, an uncompromising, elite forensic Vedic Astrologer. 
Your goal is to generate a TWO-PART MASTER OUTPUT that is mathematically accurate, psychologically impactful, but professional and non-deterministic.

[ABSOLUTE LAWS - VIOLATION = FAILURE]
1. FACTS ONLY: Do NOT invent planetary positions, degrees, or yogas. Synthesize ONLY the math provided in the user prompt.
2. HINDI MANDATORY: You MUST use the Hindi names provided for EVERY Zodiac Sign and Planet. Example: 'Leo (Simha)', 'Saturn (Shani)'. English-only names are FORBIDDEN.
3. PLAIN ENGLISH: Every time you state an astrological condition (e.g., Debilitated, Retrograde), you MUST immediately explain what it means in plain English.
4. NO DEGREES: Do NOT output raw decimal degrees (e.g., 139.02°). Use Dignity (Exalted/Debilitated) instead.
5. NO FLUFF: Do NOT use phrases like "celestial canvas," "interplay of energies," "setting the stage," or "cosmic conflicts." Be clinical and tactical.
6. NO GEMSTONES: Do NOT recommend gemstones (like Blue Sapphire). Focus on behavioral, Ayurvedic, and mantra-based remedies.
7. STRUCTURE: You MUST use the exact Two-Part structure provided below.
"""

                user_msg = f"""
[INPUT DATA]
- Baseline Date: {t_ctx['current_date']}
- Current Dasha: {t_ctx['dasha_now']}
- 5-Year Dasha: {t_ctx['dasha_5y']}
{logic_breakdown}

[PLANETARY ARRAY]
- Ascendant (Lagna): {HINDI_SIGNS[asc_sign]} in {asc_nak} Pada {asc_pada}
{planet_summary}

[OUTPUT TEMPLATE - FOLLOW EXACTLY]
*Disclaimer: This audit maps karmic tendencies and probabilistic risk vectors based on planetary mathematics. Astrological indications are environmental influences, not absolute mandates.*

# PART 1: THE EXECUTIVE BRIEF
1. **Core Planetary Matrix**
   - List Lagna, Active Dasha, and a concise bullet list of the 5 core planets (Sun, Moon, Mars, Jupiter, Saturn) with their Hindi Sign and Dignity (translated to plain English).
2. **Timeline Summary (Past, Present, Future)**
   - *Past*: Briefly state what the previous Dasha theme was.
   - *Present*: What the current Dasha is activating right now (Threats/Opportunities).
   - *Future*: What the next Dasha indicates.

# PART 2: COMPREHENSIVE FORENSIC DOSSIER
3. **Psychological Blueprint & Ayurvedic Baseline**
   - Explain mental triggers and emotional loops based strictly on the [PSYCHOLOGICAL TRIGGERS] data.
   - Detail Ayurvedic constitution (Vata/Pitta/Kapha) and physical health vulnerabilities.
4. **Strategic Domain Audit (Risk vs. Reward)**
   - Deep dive into Career, Wealth, Marriage, Legal, and Progeny/Property based on the House Map.
   - Frame this as a risk-to-reward matrix. Explicitly mention the Vector and Trigger provided in the math.
5. **5-Year Chronological Roadmap**
   - Map the current Dasha and 5-Year Dasha to specific chronological life events. 
   - State exact years and expected outcomes.
6. **Tiered Remediation Protocol (Upaayas)**
   - *Immediate First Aid*: 1-2 urgent actions.
   - *Tactical Actions*: Behavioral/Ayurvedic modifications.
   - *Long-Term Alignment*: Mantras or spiritual practices.
"""

                payload = {
                    "model": "llama-3.3-70b-versatile", 
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg}
                    ], 
                    "temperature": 0.2
                }
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}

                res = requests.post(groq_url, headers=headers, json=payload, timeout=120)
                if res.status_code == 200:
                    final_text = res.json()['choices'][0]['message']['content']
                    
                    # 3. Generate and Send PDF Document
                    send_message(chat_id, "⏳ Audit complete. Formatting Dossier and generating PDF...")
                    pdf_path = f"/tmp/Forensic_Dossier_{file_tag}.pdf"
                    
                    pdf_success = generate_master_pdf(final_text, pdf_path, f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean} (Age: {age})")
                    
                    if pdf_success and os.path.exists(pdf_path):
                        send_document(chat_id, pdf_path)
                        send_message(chat_id, "📄 **Master Forensic PDF Dossier attached above!** ⬆️\nYou can now ask specific tactical questions based on this audit.")
                    else:
                        # Fallback if PDF generation fails
                        send_message(chat_id, "⚠️ PDF generation failed on server. Sending text report instead:")
                        for i in range(0, len(final_text), 3900):
                            send_message(chat_id, final_text[i:i + 3900])
                            time.sleep(0.5)
                else:
                    send_message(chat_id, f"Groq API Error: {res.text[:150]}")
                    
            elif chat_id in USER_SESSIONS:
                session = USER_SESSIONS[chat_id]
                send_message(chat_id, "Running forensic follow-up audit...")
                
                q_prompt = f"""
[SYSTEM ROLE]
You are Panditji, an elite forensic Vedic Astrologer. Today's date is {session['t_ctx']['current_date']}.
[MANDATORY RULES]
- Give an uncompromising, direct, fact-based response.
- ALWAYS use Hindi names for planets and zodiac signs (e.g., Virgo (Kanya), Saturn (Shani)).
- STRICTLY ADHERE to the user's Life Stage. Do not give irrelevant age-based advice.
- USE PROVIDED FACTS ONLY. Do not invent aspects or yogas not listed below.
- Frame predictions as probabilistic risk vectors, not guaranteed doom.
- Address the user's specific question by referencing the exact activated vectors.

[CALCULATED LOGIC & CONTEXT]
{session['logic_breakdown']}
- Active Dasha: {session['t_ctx']['dasha_now']}
- 5-Year Horizon Dasha: {session['t_ctx']['dasha_5y']}
- Planetary Array:
{session['planet_summary']}

[USER'S SPECIFIC QUESTION]
"{user_text}"

[OUTPUT DIRECTIVE]
Provide a forensic, unvarnished response. Explicitly state the astrological trigger, the exact timeline of impact, and precise preventative measures.
"""

                payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": q_prompt}], "temperature": 0.2}
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}

                res = requests.post(groq_url, headers=headers, json=payload, timeout=90)
                if res.status_code == 200:
                    answer = res.json()['choices'][0]['message']['content']
                    for i in range(0, len(answer), 3900):
                        send_message(chat_id, answer[i:i + 3900])
                        time.sleep(0.5)
                else:
                    send_message(chat_id, "Error processing your question.")
            else:
                send_message(chat_id, "Please start by sending your birth details in format:\n`DD-MM-YYYY HH:MM City`")

    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        try:
            send_message(chat_id, "An error occurred. Please ensure the format is correct.")
        except: 
            pass
        
    return jsonify(status="success"), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
