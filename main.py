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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from xml.sax.saxutils import escape

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

USER_SESSIONS = {}

ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
HINDI_SIGNS = {"Aries": "Aries (Mesha)", "Taurus": "Taurus (Vrishabha)", "Gemini": "Gemini (Mithuna)", "Cancer": "Cancer (Karka)", "Leo": "Leo (Simha)", "Virgo": "Virgo (Kanya)", "Libra": "Libra (Tula)", "Scorpio": "Scorpio (Vrishchika)", "Sagittarius": "Sagittarius (Dhanu)", "Capricorn": "Capricorn (Makara)", "Aquarius": "Aquarius (Kumbha)", "Pisces": "Pisces (Meena)"}
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
DASHA_LORDS = [("Ketu", 7), ("Venus (Shukra)", 20), ("Sun (Surya)", 6), ("Moon (Chandra)", 10), ("Mars (Mangal)", 7), ("Rahu", 18), ("Jupiter (Guru)", 16), ("Saturn (Shani)", 19), ("Mercury (Budh)", 17)]
EXALTATION = {"Sun (Surya)": "Aries", "Moon (Chandra)": "Taurus", "Mars (Mangal)": "Capricorn", "Mercury (Budh)": "Virgo", "Jupiter (Guru)": "Cancer", "Venus (Shukra)": "Pisces", "Saturn (Shani)": "Libra", "Rahu": "Taurus", "Ketu": "Scorpio"}
DEBILITATION = {"Sun (Surya)": "Libra", "Moon (Chandra)": "Scorpio", "Mars (Mangal)": "Cancer", "Mercury (Budh)": "Pisces", "Jupiter (Guru)": "Capricorn", "Venus (Shukra)": "Virgo", "Saturn (Shani)": "Aries", "Rahu": "Scorpio", "Ketu": "Taurus"}
OWN_SIGNS = {"Sun (Surya)": ["Leo"], "Moon (Chandra)": ["Cancer"], "Mars (Mangal)": ["Aries", "Scorpio"], "Mercury (Budh)": ["Gemini", "Virgo"], "Jupiter (Guru)": ["Sagittarius", "Pisces"], "Venus (Shukra)": ["Taurus", "Libra"], "Saturn (Shani)": ["Capricorn", "Aquarius"]}
COMBUSTION_ORB = {"Moon (Chandra)": 12, "Mars (Mangal)": 17, "Mercury (Budh)": 14, "Jupiter (Guru)": 11, "Venus (Shukra)": 10, "Saturn (Shani)": 15}
MALEFICS = ["Saturn (Shani)", "Mars (Mangal)", "Rahu", "Ketu", "Sun (Surya)"]
DOSHA_MAP = {"Aries": "Pitta", "Taurus": "Kapha", "Gemini": "Vata", "Cancer": "Kapha", "Leo": "Pitta", "Virgo": "Vata", "Libra": "Vata", "Scorpio": "Kapha", "Sagittarius": "Pitta", "Capricorn": "Vata", "Aquarius": "Vata", "Pisces": "Kapha"}

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    def attempt_send(parse_mode=None):
        payload = {"chat_id": chat_id, "text": text}
        if parse_mode: payload["parse_mode"] = parse_mode
        try: return requests.post(url, json=payload, timeout=10).status_code == 200
        except: return False
    if not attempt_send("Markdown"): attempt_send(None)

def send_document(chat_id, file_path):
    url = f"{TELEGRAM_API_URL}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            return requests.post(url, data={'chat_id': chat_id}, files={'document': f}, timeout=30).status_code == 200
    except: return False

def generate_svg_chart(filename, title, asc_sign, planets_data):
    p_chart_map = {"Sun (Surya)": chart.SUN, "Moon (Chandra)": chart.MOON, "Mars (Mangal)": chart.MARS, "Mercury (Budh)": chart.MERCERY, "Jupiter (Guru)": chart.JUPITER, "Venus (Shukra)": chart.VENUS, "Saturn (Shani)": chart.SATURN, "Rahu": chart.RAHU, "Ketu": chart.KETU}
    svg_path = f"/tmp/{filename}.svg"
    north = chart.NorthChart(title, "", IsFullChart=True)
    north.set_ascendantsign(asc_sign)
    for p_name, p_data in planets_data.items():
        if p_name in p_chart_map:
            north.add_planet(p_chart_map[p_name], p_name[:2], ZODIAC_SIGNS.index(p_data["sign"]) + 1)
    north.draw("/tmp/", filename)
    return svg_path

def draw_north_chart_drawing(asc_sign, planets_data, title="Chart"):
    """Pure ReportLab native chart drawing. 100% crash-proof."""
    d = Drawing(200, 220)
    d.add(String(100, 200, title, fontSize=10, fillColor=colors.HexColor('#4A154B'), fontName='Helvetica-Bold', textAnchor='middle'))
    d.add(Rect(10, 10, 180, 180, strokeColor=colors.black, fillColor=colors.white))
    d.add(Line(10, 10, 190, 190, strokeColor=colors.black))
    d.add(Line(190, 10, 10, 190, strokeColor=colors.black))
    d.add(Line(100, 10, 10, 100, strokeColor=colors.black))
    d.add(Line(10, 100, 100, 190, strokeColor=colors.black))
    d.add(Line(100, 190, 190, 100, strokeColor=colors.black))
    d.add(Line(190, 100, 100, 10, strokeColor=colors.black))

    house_coords = {1: (100, 155), 2: (55, 155), 3: (40, 115), 4: (25, 80), 5: (40, 45), 6: (55, 35), 7: (100, 35), 8: (145, 35), 9: (160, 65), 10: (175, 100), 11: (160, 135), 12: (145, 155)}
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    d.add(String(100, 165, str(asc_idx + 1), fontSize=8, fillColor=colors.purple, fontName='Helvetica-Bold', textAnchor='middle'))

    house_planets = {i: [] for i in range(1, 13)}
    for p_name, p_data in planets_data.items():
        p_sign_idx = ZODIAC_SIGNS.index(p_data["sign"])
        house_num = ((p_sign_idx - asc_idx) % 12) + 1
        house_planets[house_num].append(p_name[:2])

    for h_num, planets in house_planets.items():
        if planets:
            x, y = house_coords[h_num]
            if len(planets) == 1:
                d.add(String(x, y, planets[0], fontSize=7, fillColor=colors.black, textAnchor='middle'))
            else:
                for i, p in enumerate(planets):
                    d.add(String(x, y - (i*8), p, fontSize=7, fillColor=colors.black, textAnchor='middle'))
    return d

def generate_master_pdf(report_text, pdf_path, birth_details_str, name_str, planet_data, asc_sign, d9_planets, d9_asc_sign):
    try:
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=45, leftMargin=45, topMargin=45, bottomMargin=45)
        styles = getSampleStyleSheet()
        
        cover_title = ParagraphStyle('CoverTitle', parent=styles['Heading1'], fontSize=28, spaceAfter=15, textColor=colors.HexColor('#4A154B'), alignment=TA_CENTER, fontName='Helvetica-Bold')
        cover_sub = ParagraphStyle('CoverSub', parent=styles['Normal'], fontSize=12, spaceAfter=10, textColor=colors.HexColor('#1D1C1D'), alignment=TA_CENTER, fontName='Helvetica')
        cover_footer = ParagraphStyle('CoverFooter', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#888888'), alignment=TA_CENTER, fontName='Helvetica-Oblique')
        
        h1_style = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=14, spaceBefore=12, spaceAfter=6, textColor=colors.white, fontName='Helvetica-Bold', backColor=colors.HexColor('#4A154B'), borderPadding=(6,6,6,6), leftIndent=0, alignment=TA_LEFT)
        h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13, spaceBefore=14, spaceAfter=4, textColor=colors.HexColor('#1D1C1D'), fontName='Helvetica-Bold')
        h3_style = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=11, spaceBefore=8, spaceAfter=2, textColor=colors.HexColor('#555555'), fontName='Helvetica-BoldOblique')
        body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=8, alignment=TA_JUSTIFY, fontName='Helvetica', textColor=colors.HexColor('#222222'))
        bullet_style = ParagraphStyle('Bullet', parent=body_style, leftIndent=20, bulletIndent=8, spaceAfter=4)
        caption_style = ParagraphStyle('Caption', parent=body_style, alignment=TA_CENTER, fontSize=9, textColor=colors.HexColor('#555555'), spaceBefore=4)
        disclaimer_style = ParagraphStyle('Disclaimer', parent=body_style, fontSize=8, textColor=colors.HexColor('#666666'), alignment=TA_JUSTIFY, backColor=colors.HexColor('#F5F5F5'), borderPadding=(8,8,8,8))
        table_cell_style = ParagraphStyle('TableCell', parent=body_style, fontSize=8, leading=10, alignment=TA_LEFT)

        story = []
        story.append(Spacer(1, 160))
        story.append(Paragraph("Astrological Audit", cover_title))
        story.append(Spacer(1, 10))
        if name_str: story.append(Paragraph(f"Prepared for: {escape(name_str)}", cover_sub))
        story.append(Paragraph(f"Birth Details: {escape(birth_details_str)}", cover_sub))
        story.append(Spacer(1, 180))
        story.append(HRFlowable(width="40%", thickness=1, color=colors.HexColor('#4A154B'), hAlign='CENTER'))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M')}", cover_footer))
        story.append(PageBreak())
        
        story.append(Paragraph("ASTROLOGICAL OVERVIEW", h1_style))
        story.append(Spacer(1, 12))
        
        try:
            d1_drawing = draw_north_chart_drawing(asc_sign, planet_data, "Rasi Chart (D1)")
            d9_drawing = draw_north_chart_drawing(d9_asc_sign, d9_planets, "Navamsha Chart (D9)")
            chart_table = Table([[d1_drawing, d9_drawing], 
                                 [Paragraph("Rasi Chart (D1)", caption_style), Paragraph("Navamsha Chart (D9)", caption_style)]])
            chart_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            story.append(chart_table)
            story.append(Spacer(1, 15))
        except Exception as e:
            print(f"Native Chart Render Error: {e}", flush=True)

        table_data = [["Planet", "Sign", "Nakshatra (Pada)", "Dignity", "Status"]]
        for p_name, p_info in planet_data.items():
            table_data.append([
                Paragraph(p_name, table_cell_style),
                Paragraph(p_info['hindi_sign'], table_cell_style),
                Paragraph(f"{p_info['nak']} (P{p_info['pada']})", table_cell_style),
                Paragraph(p_info['dignity'].split(" - ")[0], table_cell_style),
                Paragraph(f"{'Retro' if p_info['retro'] else ''} {'Combust' if p_info['combust'] else ''}", table_cell_style)
            ])
            
        planet_table = Table(table_data, colWidths=[70, 90, 110, 80, 60])
        planet_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A154B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')])
        ]))
        story.append(planet_table)
        story.append(Spacer(1, 15))

        for line in report_text.split('\n'):
            line = line.strip()
            if not line: continue
            
            safe_line = escape(line)
            safe_line = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', safe_line)
            safe_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_line)
            safe_line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', safe_line)
            
            if safe_line.startswith("# PART 1"): story.append(Paragraph("ASTROLOGICAL OVERVIEW", h1_style)); story.append(Spacer(1, 12))
            elif safe_line.startswith("# PART 2"): story.append(PageBreak()); story.append(Paragraph("COMPREHENSIVE PREDICTIONS", h1_style)); story.append(Spacer(1, 12))
            elif safe_line.startswith("# PART 3"): story.append(PageBreak()); story.append(Paragraph("COMPATIBILITY & SYNESTRY ANALYSIS", h1_style)); story.append(Spacer(1, 12))
            elif safe_line.startswith("*Disclaimer:"):
                story.append(Spacer(1, 6)); story.append(Paragraph(safe_line, disclaimer_style)); story.append(Spacer(1, 10))
            elif safe_line.startswith("### "): story.append(Paragraph(safe_line.replace("### ", ""), h3_style))
            elif re.match(r'^\d+\.\s+', safe_line):
                story.append(Paragraph(re.sub(r'^\d+\.\s+', '', safe_line), h2_style))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC'), spaceBefore=2, spaceAfter=6))
            elif safe_line.startswith("  - ") or safe_line.startswith("   - "):
                story.append(Paragraph(safe_line.replace("- ", "", 1), bullet_style, bulletText='◦'))
            elif safe_line.startswith("- "):
                story.append(Paragraph(safe_line.replace("- ", "", 1), bullet_style, bulletText='•'))
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
        res = requests.get(url, headers={'User-Agent': 'PanditjiVedicBot/1.0'}, timeout=5).json()
        if res and len(res) > 0: return float(res[0]['lat']), float(res[0]['lon']), res[0].get('display_name', city_name).split(',')[0]
    except: pass
    return 30.7333, 76.7794, city_name

def get_nakshatra_info(lon):
    nak_span = 360.0 / 27.0
    nak_idx = int(lon / nak_span) % 27
    rem = lon % nak_span
    pada = int(rem / (nak_span / 4.0)) + 1
    return nak_idx, NAKSHATRAS[nak_idx], pada, rem

def get_antardasha(moon_lon, birth_dt, target_dt):
    """Calculates exact Mahadasha and Antardasha for a specific date."""
    nak_span = 360.0 / 27.0
    nak_idx, _, _, rem = get_nakshatra_info(moon_lon)
    lord_idx = (nak_idx // 3) % 9
    
    # Total years in Vimshottari = 120
    total_jd_years = 120.0
    jd_per_year = 365.25
    
    # Find Mahadasha balance at birth
    dasha_lord, total_years = DASHA_LORDS[lord_idx]
    fraction_remaining = 1.0 - (rem / nak_span)
    years_remaining = fraction_remaining * total_years
    
    current_jd = swe.julday(target_dt.year, target_dt.month, target_dt.day)
    birth_jd = swe.julday(birth_dt.year, birth_dt.month, birth_dt.day)
    years_passed = (current_jd - birth_jd) / jd_per_year
    
    # If within first dasha
    if years_passed <= years_remaining:
        m_lord = dasha_lord
        # Antardasha calculation
        m_idx = lord_idx
        a_idx = m_idx
        a_years_total = DASHA_LORDS[a_idx][1] * (DASHA_LORDS[m_idx][1] / 120.0)
        a_years_passed = years_passed
        while a_years_passed > a_years_total:
            a_years_passed -= a_years_total
            a_idx = (a_idx + 1) % 9
            a_years_total = DASHA_LORDS[a_idx][1] * (DASHA_LORDS[m_idx][1] / 120.0)
        return f"{m_lord}-{DASHA_LORDS[a_idx][0]}"
        
    # Else iterate to find correct Mahadasha and Antardasha
    years_passed_after_balance = years_passed - years_remaining
    m_idx = (lord_idx + 1) % 9
    while years_passed_after_balance > DASHA_LORDS[m_idx][1]:
        years_passed_after_balance -= DASHA_LORDS[m_idx][1]
        m_idx = (m_idx + 1) % 9
        
    m_lord = DASHA_LORDS[m_idx][0]
    # Now find Antardasha
    a_idx = m_idx
    a_years_total = DASHA_LORDS[a_idx][1] * (DASHA_LORDS[m_idx][1] / 120.0)
    a_years_passed = years_passed_after_balance
    while a_years_passed > a_years_total:
        a_years_passed -= a_years_total
        a_idx = (a_idx + 1) % 9
        a_years_total = DASHA_LORDS[a_idx][1] * (DASHA_LORDS[m_idx][1] / 120.0)
        
    return f"{m_lord}-{DASHA_LORDS[a_idx][0]}"

def get_planet_dignity(planet, sign):
    if EXALTATION.get(planet) == sign: return "Exalted (Uchcha) - Planet is at maximum strength"
    if DEBILITATION.get(planet) == sign: return "Debilitated (Neecha) - Planet is severely weakened"
    if planet in OWN_SIGNS and sign in OWN_SIGNS[planet]: return "Own Sign (Swavritti) - Planet is strong and comfortable"
    return "Neutral"

def get_aspects(planet, house):
    aspects = [7]
    if planet == "Mars (Mangal)": aspects.extend([4, 8])
    elif planet == "Jupiter (Guru)": aspects.extend([5, 9])
    elif planet == "Saturn (Shani)": aspects.extend([3, 10])
    elif planet in ["Rahu", "Ketu"]: aspects.extend([5, 9])
    return [((house - 1 + a) % 12) + 1 for a in aspects]

def get_house_of_planet(houses, planet_name):
    for h_num, h_data in houses.items():
        if planet_name in h_data["occupants"]: return h_num
    return None

def calculate_chart_logic(asc_sign, planets_full, birth_dt):
    now = datetime.now()
    age = (now - birth_dt).days // 365
    if age < 18: life_stage = f"CHILD (Age {age}): STRICTLY focus on House 4, 5, 9. NO career/marriage predictions."
    elif 18 <= age <= 25: life_stage = f"YOUNG ADULT (Age {age}): Focus on House 9, 10, 1. No marriage timelines yet."
    elif 26 <= age <= 40: life_stage = f"ESTABLISHMENT (Age {age}): Deep dive into House 10, 7, 2, 6."
    elif 41 <= age <= 60: life_stage = f"CONSOLIDATION (Age {age}): Focus on House 11, 2, 8, 10. Address mid-life crises."
    else: life_stage = f"ELDER (Age {age}): STRICTLY focus on House 9, 12, 8, 4. NO aggressive career growth."

    sign_lords = {"Aries": "Mars (Mangal)", "Taurus": "Venus (Shukra)", "Gemini": "Mercury (Budh)", "Cancer": "Moon (Chandra)", "Leo": "Sun (Surya)", "Virgo": "Mercury (Budh)", "Libra": "Venus (Shukra)", "Scorpio": "Mars (Mangal)", "Sagittarius": "Jupiter (Guru)", "Capricorn": "Saturn (Shani)", "Aquarius": "Saturn (Shani)", "Pisces": "Jupiter (Guru)"}
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    houses = {}
    for i in range(12):
        house_num = i + 1
        sign = ZODIAC_SIGNS[(asc_idx + i) % 12]
        houses[house_num] = {"sign": sign, "hindi_sign": HINDI_SIGNS[sign], "ruler": sign_lords.get(sign, ""), "occupants": [], "aspected_by": []}
    for p_name, p_data in planets_full.items():
        for h_num, h_data in houses.items():
            if h_data["sign"] == p_data["sign"]: h_data["occupants"].append(p_name); break
    for p_name, p_data in planets_full.items():
        occ_house = get_house_of_planet(houses, p_name)
        if occ_house:
            for ah in get_aspects(p_name, occ_house): houses[ah]["aspected_by"].append(p_name)
    for h_num, h_data in houses.items():
        ruler = h_data["ruler"]
        h_data["ruler_placed_in"] = get_house_of_planet(houses, ruler) if ruler else None

    fact_sheet = "[STRICT FACT SHEET - DO NOT CALCULATE LORDSHIPS YOURSELF]\n"
    for h, data in houses.items():
        occ_str = ', '.join(data['occupants']) if data['occupants'] else 'Empty'
        asp_str = ', '.join(data['aspected_by']) if data['aspected_by'] else 'None'
        fact_sheet += f"- House {h} ({data['hindi_sign']}): Ruled by {data['ruler']}. {data['ruler']} is sitting in House {data['ruler_placed_in']}. Occupied by: {occ_str}. Aspected by: {asp_str}.\n"
    
    logic_summary = f"[LIFE STAGE FILTER - MANDATORY]: {life_stage}\n{fact_sheet}"
    
    # --- HARD DEDUCTIVE INFERENCE LOGIC ---
    inferences = []
    asc_lord = sign_lords.get(asc_sign)
    asc_lord_dignity = planets_full.get(asc_lord, {}).get("dignity", "Neutral")
    
    if asc_lord_dignity.startswith("Debilitated"): inferences.append("Lagna Lord is Debilitated: The native is facing severe clinical depression, loss of self-worth, and imposter syndrome.")
    if planets_full["Moon (Chandra)"]["dignity"].startswith("Debilitated"): inferences.append("Moon is Debilitated: The native is suffering from chronic emotional hypersensitivity, anxiety, and nervous system burnout.")
    
    # Check for Financial Crisis (Combust Saturn in 2nd or 2nd Lord afflicted)
    if "Saturn (Shani)" in houses[2]["occupants"] and planets_full["Saturn (Shani)"]["combust"]:
        inferences.append("Financial Crisis Detected: Saturn is Combust in the 2nd House (Wealth). This indicates a massive, active financial crisis, zero business returns, and frozen liquidity.")
        
    # Check for Career Collapse (10th Lord in 8th/12th)
    if houses[10]["ruler_placed_in"] in [8, 12]:
        inferences.append("Career Collapse Detected: 10th Lord is in the 8th or 12th House. This indicates sudden career termination or business shutdown.")

    logic_summary += f"\n[HARD DEDUCTIVE INFERENCES]:\n - " + "\n - ".join(inferences) if inferences else "\n[HARD DEDUCTIVE INFERENCES]: None."

    return logic_summary, age

def calculate_sidereal_chart(day, month, year, hour, minute, lat, lon):
    swe.set_ephe_path(None); swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    dt_ist = datetime(year, month, day, hour, minute)
    dt_utc = dt_ist - timedelta(hours=5, minutes=30)
    utc_decimal = dt_utc.hour + (dt_utc.minute / 60.0)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal)
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    planets = {"Sun (Surya)": swe.SUN, "Moon (Chandra)": swe.MOON, "Mars (Mangal)": swe.MARS, "Mercury (Budh)": swe.MERCURY, "Jupiter (Guru)": swe.JUPITER, "Venus (Shukra)": swe.VENUS, "Saturn (Shani)": swe.SATURN, "Rahu": swe.MEAN_NODE, "Ketu": 10}
    positions = {}; d9_positions = {}; rahu_lon = 0.0; moon_lon = 0.0; sun_lon = 0.0
    for name, p_id in planets.items():
        if name == "Ketu": lon_val = (rahu_lon + 180.0) % 360.0; speed = 0
        else:
            calc = swe.calc_ut(jdut, p_id, flags)
            if isinstance(calc, tuple):
                if isinstance(calc[0], float): lon_val = calc[0]; speed = calc[3] if len(calc) > 3 else 0.0
                elif isinstance(calc[0], tuple) and len(calc[0]) > 3: lon_val = calc[0][0]; speed = calc[0][3]
                else: lon_val = calc[0][0]; speed = 0.0
            else: lon_val = 0.0; speed = 0.0
            if name == "Rahu": rahu_lon = lon_val
            if name == "Moon (Chandra)": moon_lon = lon_val
            if name == "Sun (Surya)": sun_lon = lon_val
        sign_idx = int(lon_val / 30) % 12; sign_name = ZODIAC_SIGNS[sign_idx]
        _, nak_name, pada, _ = get_nakshatra_info(lon_val)
        dignity = get_planet_dignity(name, sign_name)
        is_retro = speed < 0 if name not in ["Sun (Surya)", "Moon (Chandra)"] else False
        is_combust = False
        if name in COMBUSTION_ORB:
            dist_to_sun = abs(lon_val - sun_lon)
            if dist_to_sun > 180: dist_to_sun = 360 - dist_to_sun
            if dist_to_sun < COMBUSTION_ORB[name]: is_combust = True
        positions[name] = {"sign": sign_name, "hindi_sign": HINDI_SIGNS[sign_name], "lon": lon_val % 360.0, "nak": nak_name, "pada": pada, "dignity": dignity, "retro": is_retro, "combust": is_combust}
        d9_sign_idx = int((lon_val % (30/9)) / (30/9)) + (sign_idx * 9); d9_sign_name = ZODIAC_SIGNS[d9_sign_idx % 12]
        d9_positions[name] = {"sign": d9_sign_name, "hindi_sign": HINDI_SIGNS[d9_sign_name]}
    try: _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags); asc_lon = ascmc[0] % 360.0
    except: asc_lon = 0.0
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]; _, asc_nak, asc_pada, _ = get_nakshatra_info(asc_lon)
    asc_d9_sign_idx = int((asc_lon % (30/9)) / (30/9)) + (ZODIAC_SIGNS.index(asc_sign) * 9); asc_d9_sign = ZODIAC_SIGNS[asc_d9_sign_idx % 12]
    
    now_dt = datetime.now()
    # Calculate exact 1-year Past, Present, 1-year Future Antardashas
    past_ad = get_antardasha(moon_lon, dt_ist, now_dt - timedelta(days=365))
    present_ad = get_antardasha(moon_lon, dt_ist, now_dt)
    future_ad = get_antardasha(moon_lon, dt_ist, now_dt + timedelta(days=365))
    
    t_ctx = {
        "current_date": now_dt.strftime("%B %d, %Y"), 
        "past_ad": past_ad, 
        "present_ad": present_ad, 
        "future_ad": future_ad
    }
    logic_breakdown, age = calculate_chart_logic(asc_sign, positions, dt_ist)
    return asc_sign, asc_nak, asc_pada, positions, d9_positions, asc_d9_sign, t_ctx, logic_breakdown, age

def calculate_synastry(p1_data, p2_data):
    p1_moon_idx, p1_nak, _, _ = get_nakshatra_info(p1_data["Moon (Chandra)"]["lon"])
    p2_moon_idx, p2_nak, _, _ = get_nakshatra_info(p2_data["Moon (Chandra)"]["lon"])
    p1_moon_sign_idx = ZODIAC_SIGNS.index(p1_data["Moon (Chandra)"]["sign"])
    p2_moon_sign_idx = ZODIAC_SIGNS.index(p2_data["Moon (Chandra)"]["sign"])
    
    nadi_dosha = (p1_moon_idx % 3) == (p2_moon_idx % 3); nadi_pts = 0 if nadi_dosha else 8
    sign_diff = abs(p1_moon_sign_idx - p2_moon_sign_idx)
    bhakoot_dosha = sign_diff in [1, 2, 6, 7]; bhakoot_pts = 0 if bhakoot_dosha else 7
    gan_map = [0, 0, 1, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2]
    p1_gan = gan_map[p1_moon_idx]; p2_gan = gan_map[p2_moon_idx]; gan_pts = 6
    if (p1_gan == 0 and p2_gan == 2) or (p1_gan == 2 and p2_gan == 0): gan_pts = 1
    
    total_pts = nadi_pts + bhakoot_pts + gan_pts
    summary = f"Compatibility Score: {total_pts}/21 (Minimum for marriage is 14).\n"
    if nadi_dosha: summary += "- NADI DOSHA DETECTED: Identical Nadi groups. High risk of health issues in progeny.\n"
    if bhakoot_dosha: summary += "- BHAKOOT DOSHA DETECTED: Moon signs in 2/12, 6/8, or 7/7 axis. Creates ego conflicts.\n"
    if gan_pts == 1: summary += "- GAN DOSHA DETECTED: Temperament mismatch (Deva vs Rakshasa).\n"
    return summary.strip()

@app.route('/', methods=['POST', 'GET'])
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "Render Persistent Bot Server is Active", 200
    try:
        update = request.get_json(silent=True)
        if not update: return jsonify(status="ignored"), 200
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]; user_text = update["message"]["text"].strip()
            groq_key = os.environ.get("GROQ_API_KEY"); groq_url = "https://api.groq.com/openai/v1/chat/completions"
            
            if user_text.startswith("/start"):
                if chat_id in USER_SESSIONS: del USER_SESSIONS[chat_id]
                send_message(chat_id, "Welcome! Send your birth details to begin your **Astrological Audit**:\n`Name DD-MM-YYYY HH:MM City`\n(e.g., `Rahul 05-09-1981 12:16 Amritsar`)\n\n_(Name is optional)_")
                return jsonify(status="success"), 200
                
            match = re.search(r'^(?:(?P<name>.+?)\s+)?(?P<day>\d{1,2})\s*[-/]\s*(?P<month>\d{1,2})\s*[-/]\s*(?P<year>\d{2,4})\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2})\s+(?P<city>.+)$', user_text)
            
            if match:
                if chat_id in USER_SESSIONS and USER_SESSIONS[chat_id].get("state") == "awaiting_partner":
                    send_message(chat_id, "⏳ Calculating partner's planetary array and mapping synastry...")
                    name_str2 = match.group("name") or "Partner"
                    day = int(match.group("day")); month = int(match.group("month")); year = int(match.group("year"))
                    hour = int(match.group("hour")); minute = int(match.group("minute")); city_input = match.group("city").strip()
                    if year < 100: year += 1900 if year > 25 else 2000
                    lat2, lon2, city_clean2 = get_coordinates(city_input)
                    p2_asc, p2_nak, p2_pada, p2_planets, _, _, p2_t_ctx, p2_logic, p2_age = calculate_sidereal_chart(day, month, year, hour, minute, lat2, lon2)
                    session = USER_SESSIONS[chat_id]; p1_data = session["planet_data"]; p2_data = p2_planets
                    session["synastry"] = calculate_synastry(p1_data, p2_data); session["partner_logic"] = p2_logic; session["partner_name"] = name_str2; session["state"] = "ready_to_generate"
                    return generate_final_pdf(chat_id, session, groq_key, groq_url)
                
                send_message(chat_id, "⏳ Calculating exact astronomical degrees, Ayurvedic doshas, and activated vectors...")
                name_str = match.group("name") or ""
                day = int(match.group("day")); month = int(match.group("month")); year = int(match.group("year"))
                hour = int(match.group("hour")); minute = int(match.group("minute")); city_input = match.group("city").strip()
                if year < 100: year += 1900 if year > 25 else 2000

                lat, lon, city_clean = get_coordinates(city_input)
                asc_sign, asc_nak, asc_pada, planets, d9_planets, asc_d9_sign, t_ctx, logic_breakdown, age = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                
                USER_SESSIONS[chat_id] = {
                    "state": "awaiting_focus",
                    "asc_sign": asc_sign, "planet_summary": "\n".join([f"- {p}: {d['hindi_sign']} | Nak: {d['nak']} (P{d['pada']}) | Dignity: {d['dignity']}" for p, d in planets.items()]),
                    "planet_data": planets, "d9_planets": d9_planets, "asc_d9_sign": asc_d9_sign, "t_ctx": t_ctx, "logic_breakdown": logic_breakdown, "age": age, "name": name_str,
                    "d1_svg": generate_svg_chart(f"d1_{chat_id}_{int(time.time())}", "Rasi (D1)", asc_sign, planets),
                    "d9_svg": generate_svg_chart(f"d9_{chat_id}_{int(time.time())}", "Navamsha (D9)", asc_d9_sign, d9_planets),
                    "birth_str": f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean} (Age: {age})"
                }
                send_message(chat_id, "✅ Chart calculated. Before I generate the brief, would you like to include anything specific you want to know about? (e.g., Health, Finances, Legal, Career, Marriage)\n\n_Reply with your focus area, or type 'skip'._")
                return jsonify(status="success"), 200

            elif chat_id in USER_SESSIONS and USER_SESSIONS[chat_id].get("state") == "awaiting_focus":
                session = USER_SESSIONS[chat_id]
                session["focus_areas"] = "General comprehensive audit." if user_text.lower() == 'skip' else user_text
                session["state"] = "awaiting_partner"
                send_message(chat_id, "Do you want to analyze compatibility with a partner? \n\nSend their details (Name DD-MM-YYYY HH:MM City) or type 'skip'.")
                return jsonify(status="success"), 200

            elif chat_id in USER_SESSIONS and USER_SESSIONS[chat_id].get("state") == "awaiting_partner":
                if user_text.lower() == 'skip':
                    session = USER_SESSIONS[chat_id]; session["state"] = "ready_to_generate"
                    return generate_final_pdf(chat_id, session, groq_key, groq_url)
                else:
                    send_message(chat_id, "Please send the partner's details in the correct format:\n`Name DD-MM-YYYY HH:MM City`\n\nOr type 'skip'.")
                    return jsonify(status="success"), 200
            
            elif chat_id in USER_SESSIONS and USER_SESSIONS[chat_id].get("state") == "ready_to_generate":
                session = USER_SESSIONS[chat_id]
                send_message(chat_id, "Running follow-up analysis...")
                q_prompt = f"""[SYSTEM ROLE]\nYou are an elite Vedic Astrologer. Today's date is {session['t_ctx']['current_date']}.\n[MANDATORY RULES]\n- Give an uncompromising, direct, fact-based response. Synthesize the data, don't just rephrase it.\n- ALWAYS use Hindi names for planets and zodiac signs.\n- USE PROVIDED FACTS ONLY. Do not invent aspects or yogas not listed below.\n\n[CALCULATED LOGIC & CONTEXT]\n{session['logic_breakdown']}\n- Planetary Array:\n{session['planet_summary']}\n\n[USER'S SPECIFIC QUESTION]\n"{user_text}"\n\n[OUTPUT DIRECTIVE]\nProvide an unvarnished response. Explicitly state the astrological trigger, the exact timeline of impact, and precise preventative measures."""
                payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": q_prompt}], "temperature": 0.3}
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
                res = requests.post(groq_url, headers=headers, json=payload, timeout=90)
                if res.status_code == 200:
                    answer = res.json()['choices'][0]['message']['content']
                    for i in range(0, len(answer), 3900): send_message(chat_id, answer[i:i + 3900]); time.sleep(0.5)
                else: send_message(chat_id, "Error processing your question.")
                return jsonify(status="success"), 200
            else:
                send_message(chat_id, "Please start by sending your birth details in format:\n`Name DD-MM-YYYY HH:MM City`")

    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        try: send_message(chat_id, "An error occurred. Please ensure the format is correct.")
        except: pass
    return jsonify(status="success"), 200

def generate_final_pdf(chat_id, session, groq_key, groq_url):
    send_message(chat_id, "⏳ Audit complete. Formatting Dossier and generating PDF...")
    
    system_msg = """You are a Forensic Astrological Diagnostician. You do not describe potentials; you diagnose hard realities based on the math. 
[ABSOLUTE LAWS - VIOLATION = FAILURE]
1. HARD DEDUCTIONS: If the data shows a crisis (e.g., Combust Saturn in 2nd, Debilitated Moon), you MUST state it bluntly. Do NOT use philosophical terms like "adaptable," "sociable," or "harmonious." The user is facing a massive financial crisis and severe depression; your report MUST explicitly reflect this brutal reality.
2. NO HALLUCINATIONS: You are strictly forbidden from inventing planetary aspects. You may ONLY mention an aspect if it is explicitly listed in the [FACT BLOCK]. If the Fact Block says "Aspected by: None", you are forbidden from mentioning any aspects.
3. HINDI MANDATORY: You MUST use the Hindi names provided for EVERY Zodiac Sign and Planet.
4. PLAIN ENGLISH: Every time you state an astrological condition, you MUST immediately explain what it means in real-world terms.
5. NO FLUFF: Be clinical, tactical, and direct. Words like 'interplay' or 'energies' are FORBIDDEN.
6. ACTIONABLE REMEDIES: Do NOT use vague phrases like "manage stress". Remedies must be hyper-specific physical actions, donations, gemstones, or mantras.
"""

    logic = session['logic_breakdown']
    
    def extract_house_facts(house_num):
        match = re.search(rf"- House {house_num} \((.*?)\): Ruled by (.*?)\. .*? is sitting in House (\d+)\. Occupied by: (.*?)\. Aspected by: (.*?)\.", logic)
        if match:
            sign, lord, lord_house, occ, asp = match.groups()
            return f"House {house_num} is {sign}. Ruled by {lord}. Lord is in House {lord_house}. Occupied by: {occ}. Aspected by: {asp}."
        return f"Data for House {house_num} not found."

    h2_facts = extract_house_facts(2)
    h7_facts = extract_house_facts(7)
    h10_facts = extract_house_facts(10)
    h11_facts = extract_house_facts(11)
    h6_facts = extract_house_facts(6)
    h8_facts = extract_house_facts(8)
    h12_facts = extract_house_facts(12)

    synastry_block = ""
    if "synastry" in session:
        synastry_block = f"""
# PART 3: COMPATIBILITY & SYNESTRY ANALYSIS
9. **Partnership Dynamics (with {session.get('partner_name', 'Partner')})**
   - Analyze the compatibility data provided below. Explain the psychological and karmic implications of any Doshas detected (Nadi, Bhakoot, Gan).
   - Provide a clear risk-to-reward assessment of the partnership.
   - Detail specific remedies to mitigate friction in the relationship.
"""

    user_msg = f"""[INPUT DATA]
- Baseline Date: {session['t_ctx']['current_date']}
- Exact Past Antardasha (1 year ago): {session['t_ctx']['past_ad']}
- Exact Present Antardasha (Active now): {session['t_ctx']['present_ad']}
- Exact Future Antardasha (1 year from now): {session['t_ctx']['future_ad']}
{session['logic_breakdown']}

[USER FOCUS AREAS]: {session['focus_areas']}

[PLANETARY ARRAY]
- Ascendant (Lagna): {HINDI_SIGNS[session['asc_sign']]}
{session['planet_summary']}
"""

    if "synastry" in session:
        user_msg += f"""
[PARTNER COMPATIBILITY DATA]
{session['synastry']}
[PARTNER PLANETARY LOGIC]
{session.get('partner_logic', 'N/A')}
"""

    user_msg += f"""
[OUTPUT TEMPLATE - FOLLOW EXACTLY]
*Disclaimer: This audit maps karmic tendencies and probabilistic risk vectors based on planetary mathematics. Astrological indications are environmental influences, not absolute mandates.*

# PART 1: ASTROLOGICAL OVERVIEW
1. **Nakshatra & Planetary Brief**
   - Explicitly state the Ascendant Nakshatra and Moon Nakshatra. Explain exactly what psychological traits they grant the user. 
   - List Lagna, Lagna Lord, Active Dasha, and the 5 core planets with their Hindi Sign and Dignity. Explain what the dignity means (e.g., "Combust Saturn means financial actions are completely burned up and failing").

# PART 2: COMPREHENSIVE PREDICTIONS
2. **Timeline & Life Stage Context (1-Year Windows)**
   - *Past (Last 1 Year)*: Based on the Exact Past Antardasha, describe the psychological and situational impact of that period.
   - *Present (Current)*: Based on the Exact Present Antardasha, synthesize the current state. Explicitly mention the financial crisis, lack of business returns, and severe depression if indicated by the [HARD DEDUCTIVE INFERENCES].
   - *Future (Next 1 Year)*: Based on the Exact Future Antardasha, describe the expected shift or continuation of themes.
3. **Career & Professional Trajectory**
   - [FACT BLOCK FOR 10TH HOUSE]: {h10_facts}
   - Directive: First, list 2-3 career models most suitable according to the 10th Lord and Nakshatra placement. Then, write 2 paragraphs providing a SITUATIONAL ANALYSIS of the current state of their career (e.g., business shutdown, job loss). DO NOT mention any aspects not listed in the Fact Block.
4. **Wealth & Financial Assets**
   - [FACT BLOCK FOR 2ND HOUSE]: {h2_facts}
   - [FACT BLOCK FOR 11TH HOUSE]: {h11_facts}
   - Directive: Write 2 paragraphs providing a SITUATIONAL ANALYSIS of their financial life. Explicitly diagnose the current massive financial crisis and liquidity freeze based on the Combust Saturn. DO NOT mention any aspects not listed.
5. **Marriage & Relationship Dynamics**
   - [FACT BLOCK FOR 7TH HOUSE]: {h7_facts}
   - Directive: Write 2 paragraphs providing a SITUATIONAL ANALYSIS of their marriage/partnerships. Focus on the psychological friction and emotional distance. DO NOT mention any aspects not listed.
6. **Health & Legal Risk Vectors**
   - [FACT BLOCK FOR 6TH HOUSE]: {h6_facts}
   - [FACT BLOCK FOR 8TH HOUSE]: {h8_facts}
   - [FACT BLOCK FOR 12TH HOUSE]: {h12_facts}
   - Directive: Write 2 paragraphs providing a SITUATIONAL ANALYSIS of health/legal vulnerabilities. Explicitly state the severe clinical depression, anxiety, and nervous system burnout indicated by the [HARD DEDUCTIVE INFERENCES]. DO NOT mention any aspects not listed.
7. **Ayurvedic Baseline & Constitution**
   - Detail Dosha and explain exactly how it physically manifests the severe psychological stress (e.g., Vata imbalance causing panic attacks and insomnia). Provide specific dietary advice to stabilize the nervous system.
8. **Remediation Protocols (Upaayas)**
   - *Immediate First Aid*: 1-2 urgent, specific actions targeting the most critical threat vector (Financial/Depression).
   - *Lal Kitab Remedies*: Provide 2-3 highly specific Lal Kitab remedies for the afflicted planets (e.g., feeding specific animals, burying specific items).
   - *Ayurvedic/Behavioral*: Specific lifestyle/dietary shifts for their exact Dosha to cure the anxiety.
   - *Gemstone Enhancement*: Recommend 1-2 specific gemstones for beneficial planets. Include the exact metal to set it in, the finger to wear it on, and the day to activate it.
   - *Mantra/Long-Term Alignment*: Specific mantras for the Lagna Lord or afflicted planets to rebuild self-worth and financial stability.
   (FORBIDDEN WORDS: "manage stress", "practice mindfulness", "seek balance", "self-care". Be hyper-specific and actionable).
{synastry_block}
"""

    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}], "temperature": 0.3}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
    res = requests.post(groq_url, headers=headers, json=payload, timeout=120)
    
    if res.status_code == 200:
        final_text = res.json()['choices'][0]['message']['content']
        file_tag = str(int(time.time()))
        pdf_path = f"/tmp/Astrological_Audit_{file_tag}.pdf"
        pdf_success = generate_master_pdf(final_text, pdf_path, session["birth_str"], session["name"], session["planet_data"], session["asc_sign"], session["d9_planets"], session["asc_d9_sign"])
        
        if pdf_success and os.path.exists(pdf_path):
            send_document(chat_id, pdf_path)
            send_message(chat_id, "📄 **Astrological Audit PDF attached above!** ⬆️\nYou can now ask specific tactical questions based on this audit.")
        else:
            send_message(chat_id, "⚠️ PDF generation failed on server. Sending text report instead:")
            for i in range(0, len(final_text), 3900): send_message(chat_id, final_text[i:i + 3900]); time.sleep(0.5)
    else:
        send_message(chat_id, f"Groq API Error: {res.text[:150]}")
    return jsonify(status="success"), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
