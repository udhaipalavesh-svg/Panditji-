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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

USER_SESSIONS = {}

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

# --- ASTROLOGICAL MATH DICTIONARIES ---
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
# Combustion degrees (approximate orb)
COMBUSTION_ORB = {
    "Moon (Chandra)": 12, "Mars (Mangal)": 17, "Mercury (Budh)": 14,
    "Jupiter (Guru)": 11, "Venus (Shukra)": 10, "Saturn (Shani)": 15
}

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    def attempt_send(parse_mode=None):
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode: payload["parse_mode"] = parse_mode
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
    except Exception as e:
        print(f"Exception in send_document: {e}", flush=True)

def generate_pdf_report(report_text, pdf_path, birth_details_str):
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=8, textColor=colors.HexColor('#4A154B'), alignment=1)
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=12, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#1D1C1D'))
    body_style = ParagraphStyle('ReportBody', parent=styles['Normal'], fontSize=9.5, leading=14, spaceAfter=6, alignment=TA_JUSTIFY)

    story = []
    story.append(Paragraph("<b>Panditji - Forensic Astrological & Catastrophic Risk Audit</b>", title_style))
    story.append(Paragraph(f"<b>Client Profile:</b> {birth_details_str}", body_style))
    story.append(Spacer(1, 12))

    report_text_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', report_text)

    for line in report_text_html.split('\n'):
        line = line.strip()
        if not line: continue
        if re.match(r'^\d+\.\s+<b>', line) or line.startswith("# <b>"):
            story.append(Spacer(1, 6))
            story.append(Paragraph(line, heading_style))
        else:
            story.append(Paragraph(line, body_style))

    doc.build(story)

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
    if EXALTATION.get(planet) == sign: return "Exalted (Uchcha)"
    if DEBILITATION.get(planet) == sign: return "Debilitated (Neecha)"
    if planet in OWN_SIGNS and sign in OWN_SIGNS[planet]: return "Own Sign (Swavritti)"
    return "Neutral"

def get_aspects(planet, house):
    aspects = [7] # All planets aspect 7th
    if planet == "Mars (Mangal)": aspects.extend([4, 8])
    elif planet == "Jupiter (Guru)": aspects.extend([5, 9])
    elif planet == "Saturn (Shani)": aspects.extend([3, 10])
    elif planet in ["Rahu", "Ketu"]: aspects.extend([5, 9]) # Standard Rahu/Ketu aspects
    return [((house - 1 + a) % 12) + 1 for a in aspects]

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
        houses[house_num] = {"sign": sign, "ruler": sign_lords.get(sign, ""), "occupants": [], "aspected_by": []}
        
    # Map occupants
    for p_name, p_data in planets_full.items():
        for h_num, h_data in houses.items():
            if h_data["sign"] == p_data["sign"]:
                h_data["occupants"].append(p_name)
                break
                
    # Map Aspects
    for p_name, p_data in planets_full.items():
        occ_house = None
        for h_num, h_data in houses.items():
            if p_name in h_data["occupants"]:
                occ_house = h_num
                break
        if occ_house:
            aspected_houses = get_aspects(p_name, occ_house)
            for ah in aspected_houses:
                houses[ah]["aspected_by"].append(p_name)

    # Detect Key Yogas
    yogas = []
    for p_name, p_data in planets_full.items():
        if p_name in ["Mars (Mangal)", "Mercury (Budh)", "Jupiter (Guru)", "Venus (Shukra)", "Saturn (Shani)"]:
            occ_house = None
            for h_num, h_data in houses.items():
                if p_name in h_data["occupants"]: occ_house = h_num
            if occ_house in [1, 4, 7, 10] and p_data["dignity"] == "Exalted (Uchcha)":
                yogas.append(f"{p_name.split(' ')[0]} causes Pancha Mahapurusha Yoga (Exalted in Kendra)")
            if occ_house in [1, 4, 7, 10] and p_data["dignity"] == "Own Sign (Swavritti)":
                yogas.append(f"{p_name.split(' ')[0]} causes Pancha Mahapurusha Yoga (Own Sign in Kendra)")

    logic_summary = f"[LIFE STAGE FILTER - MANDATORY]: {life_stage}\n[PROGRAMMATIC HOUSE MAP]:\n"
    for h, data in houses.items():
        logic_summary += f"  House {h} ({data['sign']}, Ruled by {data['ruler']}): Occupied by {data['occupants'] if data['occupants'] else 'Empty'}. Aspected by {data['aspected_by'] if data['aspected_by'] else 'None'}.\n"
    
    if yogas:
        logic_summary += f"\n[DETECTED YOGAS]: {', '.join(yogas)}\n"
        
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
    rahu_lon = 0.0
    moon_lon = 0.0
    sun_lon = 0.0
    
    for name, p_id in planets.items():
        if name == "Ketu":
            lon_val = (rahu_lon + 180.0) % 360.0
            speed = 0
        else:
            calc = swe.calc_ut(jdut, p_id, flags)
            lon_val = calc[0] if isinstance(calc[0], float) else calc[0][0]
            speed = calc[3] if isinstance(calc[3], float) else calc[3][0]
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
            if dist_to_sun > 180: dist_to_sun = 360 - dist_to_sun
            if dist_to_sun < COMBUSTION_ORB[name]:
                is_combust = True
                
        positions[name] = {
            "sign": sign_name, "lon": lon_val % 360.0, "nak": nak_name, "pada": pada,
            "dignity": dignity, "retro": is_retro, "combust": is_combust
        }
        
    try:
        _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags)
        asc_lon = ascmc[0] % 360.0
    except Exception:
        asc_lon = 0.0
        
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]
    _, asc_nak, asc_pada, _ = get_nakshatra_info(asc_lon)
    
    now_dt = datetime.now()
    active_dasha = calculate_vimshottari_dasha(moon_lon, dt_ist, now_dt)
    
    t_ctx = {
        "current_date": now_dt.strftime("%B %d, %Y"),
        "dasha_now": active_dasha,
        "dasha_5y": calculate_vimshottari_dasha(moon_lon, dt_ist, now_dt + timedelta(days=365 * 5))
    }
    
    logic_breakdown, age = calculate_chart_logic(asc_sign, positions, dt_ist)
    return asc_sign, asc_nak, asc_pada, positions, t_ctx, logic_breakdown, age

@app.route('/', methods=['POST', 'GET'])
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Render Persistent Bot Server is Active", 200
        
    try:
        update = request.get_json(silent=True)
        if not update: return jsonify(status="ignored"), 200
            
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"].strip()
            
            groq_key = os.environ.get("GROQ_API_KEY")
            groq_url = "https://api.groq.com/openai/v1/chat/completions"
            
            if user_text.startswith("/start"):
                if chat_id in USER_SESSIONS: del USER_SESSIONS[chat_id]
                welcome_msg = "Welcome! Send your birth details to receive your **Forensic Astrological Report**:\n`DD-MM-YYYY HH:MM City`\n(e.g., `05-09-1981 12:16 Amritsar`)"
                send_message(chat_id, welcome_msg)
                return jsonify(status="success"), 200
                
            match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})\s+(.+)', user_text)
            
            if match:
                send_message(chat_id, "Calculating exact astronomical degrees, planetary dignities, aspects, and compiling PDF dossier...")
                
                day, month, year, hour, minute, city_input = match.groups()
                day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                city_input = city_input.strip()

                lat, lon, city_clean = get_coordinates(city_input)
                asc_sign, asc_nak, asc_pada, planets, t_ctx, logic_breakdown, age = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                
                planet_summary = "\n".join([f"- {p}: {d['sign']} | Deg: {d['lon']:.2f}° | Nak: {d['nak']} (P{d['pada']}) | Dignity: {d['dignity']} {'[Retrograde]' if d['retro'] else ''} {'[Combust]' if d['combust'] else ''}" for p, d in planets.items()])
                
                USER_SESSIONS[chat_id] = {
                    "asc_sign": asc_sign, "planet_summary": planet_summary, "t_ctx": t_ctx, 
                    "logic_breakdown": logic_breakdown, "age": age
                }
                
                os.makedirs("/tmp", exist_ok=True)
                file_tag = str(int(time.time()))
                
                # 1. SVG Chart
                svg_filename = f"natal_chart_{file_tag}"
                svg_path = f"/tmp/{svg_filename}.svg"
                north = chart.NorthChart("Natal Chart (Lahiri)", f"{day:02d}-{month:02d}-{year} ({city_clean})", IsFullChart=True)
                north.set_ascendantsign(asc_sign)
                
                p_map = {"Sun (Surya)": chart.SUN, "Moon (Chandra)": chart.MOON, "Mars (Mangal)": chart.MARS, "Mercury (Budh)": chart.MERCURY, "Jupiter (Guru)": chart.JUPITER, "Venus (Shukra)": chart.VENUS, "Saturn (Shani)": chart.SATURN, "Rahu": chart.RAHU, "Ketu": chart.KETU}
                for p_name, p_code in p_map.items():
                    if p_name in planets:
                        north.add_planet(p_code, p_name[:2], ZODIAC_SIGNS.index(planets[p_name]["sign"]) + 1)
                north.draw("/tmp/", svg_filename)
                send_document(chat_id, svg_path)

                # 2. Forensic Audit Prompt
                prompt = f"""
[SYSTEM ROLE]
You are Panditji, an uncompromising, elite forensic Vedic Astrologer. Today's date is {t_ctx['current_date']}.

[STRICT RULES - ZERO TOLERANCE FOR VIOLATIONS]
1. **USE PROVIDED FACTS ONLY**: Do NOT invent planetary positions, aspects, or yogas. Synthesize ONLY the math provided in the [CALCULATED LOGIC] block.
2. **NO VAGUE GENERALITIES**: State *precisely* what restrictions or risks apply based on the exact dignity (Exalted/Debilitated) and aspects provided.
3. **HINDI NOMENCLATURE MANDATE**: Include Hindi names in brackets for EVERY planetary reference (e.g., Saturn (Shani)).
4. **STRICT AGE COMPLIANCE**: ONLY discuss topics relevant to the [LIFE STAGE FILTER]. 
5. **ACTIONABLE UPAYAS**: Remedies must be highly specific (e.g., "Donate black sesame oil on Saturday evening").

[CALCULATED ASTROLOGICAL FACTS]
- Baseline Date: {t_ctx['current_date']}
- Current Dasha: {t_ctx['dasha_now']}
- 5-Year Dasha: {t_ctx['dasha_5y']}
{logic_breakdown}

[PLANETARY ARRAY]
- Ascendant (Lagna): {asc_sign} in {asc_nak} Pada {asc_pada}
{planet_summary}

[OUTPUT DIRECTIVE]
Generate a master-level forensic audit structured strictly into these 6 sections. Use Markdown (** for bold):

1. **Executive Summary & Age-Contextual Baseline**
   - Synthesize the core theme based on Ascendant and Moon dignity.
   - Explicitly state what life areas are in focus based on the user's age.

2. **Forensic Planetary Synthesis**
   - Analyze the impact of planets that are Exalted, Debilitated, Retrograde, or Combust.
   - Explain how the planetary aspects (Drishti) modify the houses they touch.

3. **Cosmic Conflicts & Karmic Entrapments**
   - Identify exact conflicts based on house occupants and rulers.
   - Explain the psychological or physical confinement they cause.

4. **Age-Calibrated Time-Bracketed Roadmap (Next 5 Years)**
   - Map the current Dasha and 5-Year Dasha to specific life events.

5. **Catastrophic Risk Scanner**
   - *Health Vulnerabilities*: Based on 6th/8th/12th house occupants/aspects.
   - *Financial & Legal Threats*: Fraud, bankruptcy, or confinement triggers.
   - *Relationship Threats*: Alienation or divorce (ONLY if age appropriate).

6. **Tactical Remediation Protocol (Upaayas)**
   - Step-by-step actions to mitigate risks identified in Section 5.
"""

                payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}

                res = requests.post(groq_url, headers=headers, json=payload, timeout=90)
                if res.status_code == 200:
                    final_text = res.json()['ch
