import os
import requests
import re
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import swisseph as swe
import jyotichart as chart
import time

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

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
            res = requests.post(url, data=data, files=files, timeout=20)
            print(f"SendDocument status: {res.status_code}", flush=True)
    except Exception as e:
        print(f"Exception in send_document: {e}", flush=True)

def generate_pdf_report(report_text, pdf_path, birth_details_str):
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        textColor=styles['colors'].HexColor('#4A154B') if hasattr(styles, 'colors') else None
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=4,
        textColor=styles['colors'].HexColor('#1D1C1D') if hasattr(styles, 'colors') else None
    )
    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=6
    )

    story = []
    story.append(Paragraph("<b>Panditji - Master Vedic Astrological Blueprint</b>", title_style))
    story.append(Paragraph(f"<b>Client Profile / Details:</b> {birth_details_str}", body_style))
    story.append(Spacer(1, 10))

    for line in report_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith("**") and "**" in line[2:]:
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

def calculate_chart_logic(asc_sign, planets, birth_dt):
    now = datetime.now()
    age = (now - birth_dt).days // 365
    
    if age < 18:
        life_stage = f"MINOR / STUDENT (Age {age}): Focus strictly on House 5 (Education, Learning Aptitude, Memory), House 4 (Foundational Happiness, Mother, Home), and House 9 (Higher Guidance/Mentorship). Do NOT discuss adult career shifts, marriage, or financial investments."
    else:
        life_stage = f"ADULT / PROFESSIONAL (Age {age}): Focus on Career (House 10), Wealth/Assets (House 2 & 11), Relationships (House 7), and Life Path."

    sign_lords = {
        "Aries": "Mars (Mangal)", "Taurus": "Venus (Shukra)", "Gemini": "Mercury (Budh)",
        "Cancer": "Moon (Chandra)", "Leo": "Sun (Surya)", "Virgo": "Mercury (Budh)",
        "Libra": "Venus (Shukra)", "Scorpio": "Mars (Mangal)", "Sagittarius": "Jupiter (Guru)",
        "Capricorn": "Saturn (Shani)", "Aquarius": "Saturn (Shani)", "Pisces": "Jupiter (Guru)"
    }
    
    zodiac_order = ZODIAC_SIGNS
    try:
        asc_idx = zodiac_order.index(asc_sign)
    except ValueError:
        asc_idx = 0
        
    houses = {}
    for i in range(12):
        house_num = i + 1
        sign = zodiac_order[(asc_idx + i) % 12]
        ruler = sign_lords.get(sign, "")
        houses[house_num] = {"sign": sign, "ruler": ruler, "occupants": []}
        
    for p_name, (p_sign, _, _, _) in planets.items():
        for h_num, h_data in houses.items():
            if h_data["sign"] == p_sign:
                h_data["occupants"].append(p_name)
                
    logic_summary = f"[LIFE STAGE FILTER]: {life_stage}\n[PROGRAMMATIC HOUSE MAP]:\n"
    for h, data in houses.items():
        logic_summary += f"  House {h} ({data['sign']}, Ruled by {data['ruler']}): Occupied by {data['occupants'] if data['occupants'] else 'Empty'}\n"
        
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
    for name, p_id in planets.items():
        if name == "Ketu":
            lon_val = (rahu_lon + 180.0) % 360.0
        else:
            calc = swe.calc_ut(jdut, p_id, flags)
            lon_val = calc[0] if isinstance(calc[0], float) else calc[0][0]
            if name == "Rahu": rahu_lon = lon_val
            if name == "Moon (Chandra)": moon_lon = lon_val
                
        sign_idx = int(lon_val / 30) % 12
        sign_name = ZODIAC_SIGNS[sign_idx]
        _, nak_name, pada, _ = get_nakshatra_info(lon_val)
        positions[name] = (sign_name, lon_val % 360.0, nak_name, pada)
        
    try:
        _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags)
        asc_lon = ascmc[0] % 360.0
    except Exception:
        asc_lon = 0.0
        
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]
    _, asc_nak, asc_pada, _ = get_nakshatra_info(asc_lon)
    
    now_dt = datetime.now()
    active_dasha = calculate_vimshottari_dasha(moon_lon, dt_ist, now_dt)
    
    temporal_context = {
        "current_date": now_dt.strftime("%B %d, %Y"),
        "dasha_now": active_dasha,
        "dasha_6m": calculate_vimshottari_dasha(moon_lon, dt_ist, now_dt + timedelta(days=182)),
        "dasha_1y": calculate_vimshottari_dasha(moon_lon, dt_ist, now_dt + timedelta(days=365)),
        "dasha_5y": calculate_vimshottari_dasha(moon_lon, dt_ist, now_dt + timedelta(days=365 * 5)),
        "dasha_10y": calculate_vimshottari_dasha(moon_lon, dt_ist, now_dt + timedelta(days=365 * 10))
    }
    
    logic_breakdown, age = calculate_chart_logic(asc_sign, positions, dt_ist)
    return asc_sign, asc_nak, asc_pada, positions, temporal_context, logic_breakdown, age

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
                    
                welcome_msg = "Welcome! Send your birth details to receive your age-adapted astrological report and PDF (including 5-year bracket predictions):\nDD-MM-YYYY HH:MM City\n(e.g., 05-09-1981 12:16 Amritsar)"
                send_message(chat_id, welcome_msg)
                return jsonify(status="success"), 200
                
            match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})\s+(.+)', user_text)
            
            if match:
                send_message(chat_id, "Calculating life-stage age filter, temporal dasha brackets (including 5-year macro blocks), and compiling PDF...")
                
                day, month, year, hour, minute, city_input = match.groups()
                day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                city_input = city_input.strip()

                lat, lon, city_clean = get_coordinates(city_input)
                asc_sign, asc_nak, asc_pada, planets, t_ctx, logic_breakdown, age = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                
                planet_summary = "\n".join([f"- {p}: {info[0]} | Exact Deg: {info[1]:.2f}° | Nakshatra: {info[2]} (Pada {info[3]})" for p, info in planets.items()])
                
                USER_SESSIONS[chat_id] = {
                    "asc_sign": asc_sign,
                    "asc_nak": asc_nak,
                    "asc_pada": asc_pada,
                    "planet_summary": planet_summary,
                    "t_ctx": t_ctx,
                    "logic_breakdown": logic_breakdown,
                    "age": age
                }
                
                os.makedirs("/tmp", exist_ok=True)
                file_tag = str(int(time.time()))
                
                # SVG Chart
                svg_filename = f"natal_chart_{file_tag}"
                svg_path = f"/tmp/{svg_filename}.svg"
                north = chart.NorthChart("Natal Chart (Lahiri)", f"{day:02d}-{month:02d}-{year} ({city_clean})", IsFullChart=True)
                north.set_ascendantsign(asc_sign)
                
                p_map = {
                    "Sun (Surya)": chart.SUN, "Moon (Chandra)": chart.MOON, "Mars (Mangal)": chart.MARS,
                    "Mercury (Budh)": chart.MERCURY, "Jupiter (Guru)": chart.JUPITER, "Venus (Shukra)": chart.VENUS,
                    "Saturn (Shani)": chart.SATURN, "Rahu": chart.RAHU, "Ketu": chart.KETU
                }
                for p_name, p_code in p_map.items():
                    if p_name in planets:
                        sign_name, _, _, _ = planets[p_name]
                        north.add_planet(p_code, p_name[:2], ZODIAC_SIGNS.index(sign_name) + 1)
                        
                north.draw("/tmp/", svg_filename)
                send_document(chat_id, svg_path)

                prompt = f"""
[SYSTEM ROLE]
You are Panditji, an elite master Vedic Astrologer and tactical life strategist. Today's strict baseline anchor date is {t_ctx['current_date']}.

[MANDATORY SYSTEM RULES]
1. **AGE & LIFE-STAGE LOGIC**: Adhere strictly to the calculated age filter provided below. If the user is a minor, focus on education, aptitude, health, and upbringing. Do NOT discuss adult topics.
2. **HINDI NOMENCLATURE MANDATE**: Include Hindi names in brackets for EVERY planetary reference (e.g., Saturn (Shani), Moon (Chandra)).
3. **PROGRAMMATIC HOUSE LOGIC**: Base all house interpretations strictly on the pre-calculated House Map provided below.
4. **5-YEAR & 10-YEAR BRACKETED PREDICTIONS**: Section 5 MUST explicitly detail macro predictions structured across 5-year and 10-year structural windows.

[CALCULATED ASTROLOGICAL, TEMPORAL & AGE LOGIC]
- Baseline Anchor Date (Today): {t_ctx['current_date']}
- Current Active Dasha: {t_ctx['dasha_now']}
- 6-Month Window Dasha: {t_ctx['dasha_6m']}
- 1-Year Window Dasha: {t_ctx['dasha_1y']}
- 5-Year Window Dasha: {t_ctx['dasha_5y']}
- 10-Year Window Dasha: {t_ctx['dasha_10y']}
{logic_breakdown}

[INPUT DATA]
- Ascendant (Lagna): {asc_sign} in {asc_nak} Pada {asc_pada}
- Planetary Array:
{planet_summary}

[OUTPUT DIRECTIVE]
Generate a master-level tactical blueprint structured strictly into these 8 sections:
1. **Star & Nakshatra Brief**
2. **Detailed Star Positions**
3. **Cosmic Conflicts**
4. **General Life Prediction (Age-Appropriate)**
5. **Detailed Manifestations & High-Impact Time-Bracketed Roadmap**:
   - *Immediate Present (Active Now)*
   - *Next 6 Months*
   - *6 Months to 1 Year*
   - *5-Year Long-Term Macro Block*
   - *10-Year Strategic Horizon*
6. **Karmic Liabilities & Confinement (Bandhana Yoga)**
7. **Corrective Remedies (Upaayas)**
8. **Rare Yogas & Anomalies**
"""

                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}

                res = requests.post(groq_url, headers=headers, json=payload, timeout=90)
                if res.status_code == 200:
                    final_text = res.json()['choices'][0]['message']['content']
                    pdf_path = f"/tmp/Astrological_Report_{file_tag}.pdf"
                    generate_pdf_report(final_text, pdf_path, f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean} (Age: {age})")
                    send_document(chat_id, pdf_path)
                    send_message(chat_id, "📄 **Master PDF Report & Chart Delivered (Featuring 5-Year Macro Predictions)!** You can now ask specific questions.")
                else:
                    send_message(chat_id, f"Groq API Error: {res.text[:150]}")
                    
            elif chat_id in USER_SESSIONS:
                session = USER_SESSIONS[chat_id]
                send_message(chat_id, "Consulting your chart with age-appropriate and macro-bracket logic...")
                
                q_prompt = f"""
[SYSTEM ROLE]
You are Panditji, an elite master Vedic Astrologer. Today's date is {session['t_ctx']['current_date']}.

[MANDATORY RULES]
- Adhere to the client's age-bracket ({session['age']} years old). 
- Always include Hindi names in brackets for every planet referenced.

[CALCULATED LOGIC & CONTEXT]
{session['logic_breakdown']}
- Active Dasha: {session['t_ctx']['dasha_now']}
- 5-Year Horizon Dasha: {session['t_ctx']['dasha_5y']}
- Planetary Array:
{session['planet_summary']}

[USER'S SPECIFIC QUESTION]
"{user_text}"

[OUTPUT DIRECTIVE]
Provide an uncompromising, astrologically grounded response addressing the question directly based on their age, house map, and long-term 5-year macro outlook.
"""

                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": q_prompt}],
                    "temperature": 0.7
                }
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}

                res = requests.post(groq_url, headers=headers, json=payload, timeout=60)
                if res.status_code == 200:
                    answer = res.json()['choices'][0]['message']['content']
                    for i in range(0, len(answer), 4000):
                        send_message(chat_id, answer[i:i + 4000])
                        time.sleep(0.5)
                else:
                    send_message(chat_id, "Error processing your question. Please try again.")
            else:
                send_message(chat_id, "Please start by sending your birth details in format:\nDD-MM-YYYY HH:MM City")

    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        
    return jsonify(status="success"), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
