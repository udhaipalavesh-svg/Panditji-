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

# Nakshatra Lords Mapping
NAK_LORDS = ["Ketu", "Venus (Shukra)", "Sun (Surya)", "Moon (Chandra)", "Mars (Mangal)", "Rahu", "Jupiter (Guru)", "Saturn (Shani)", "Mercury (Budh)"]

def get_nakshatra_lord(nak_idx):
    return NAK_LORDS[nak_idx % 9]

# ==========================================
# YOGA ENGINE INTEGRATED
# ==========================================
def detect_yogas(houses_dict, planets_dict):
    yogas = []
    def get_house(planet_name):
        for h_num, h_data in houses_dict.items():
            if planet_name in h_data["occupants"]: return h_num
        return None

    moon_house = get_house("Moon (Chandra)")
    jup_house = get_house("Jupiter (Guru)")
    mars_house = get_house("Mars (Mangal)")
    sat_house = get_house("Saturn (Shani)")
    rahu_house = get_house("Rahu")

    if moon_house:
        h2_moon = (moon_house % 12) + 1
        h12_moon = (moon_house - 2) % 12 + 1
        invalid_planets = ["Sun (Surya)", "Rahu", "Ketu", "Moon (Chandra)"]
        adj_planets = houses_dict[moon_house]["occupants"] + houses_dict[h2_moon]["occupants"] + houses_dict[h12_moon]["occupants"]
        valid_adj = [p for p in adj_planets if p not in invalid_planets]
        
        if not valid_adj:
            kendra_planets = houses_dict[1]["occupants"] + houses_dict[4]["occupants"] + houses_dict[7]["occupants"] + houses_dict[10]["occupants"]
            valid_kendra = [p for p in kendra_planets if p not in invalid_planets]
            if not valid_kendra:
                yogas.append("Kemadruma Yoga (No valid planets in 2nd/12th from Moon, no Bhanga cancellation in Kendras): Strict classical result indicates severe psychological isolation, mental anguish, and financial struggles in early life. If Moon is strong, it grants immense self-reliance.")

    if moon_house and jup_house:
        diff = abs(jup_house - moon_house)
        if diff in [0, 3, 6, 9]: 
            yogas.append("Gaja Kesari Yoga (Jupiter in Kendra from Moon): Strict classical result grants high intelligence, fame, wealth, strong moral character, and the ability to influence masses.")

    if jup_house and rahu_house:
        if jup_house == rahu_house:
            yogas.append("Guru Chandal Yoga (Jupiter conjunct Rahu): Strict classical result indicates distortion of wisdom, unethical associations, and karmic tests of integrity.")

    if sat_house and mars_house:
        if sat_house == mars_house:
            yogas.append("Shani-Mangal Dosha (Saturn conjunct Mars): Strict classical result indicates intense frustration, structural conflicts, property disputes, and a high risk of accidents or surgical interventions.")
    return yogas

# ==========================================
# LAL KITAB ENGINE INTEGRATED
# ==========================================
LAL_KITAB_DICT = {
    "Saturn (Shani)_Combust": "Donate black sesame oil on Saturday. Keep a square piece of silver in wallet to prevent liquid cash evaporation.",
    "Mars (Mangal)_Combust": "Donate red masoor dal on Tuesday. Avoid keeping iron tools under the bed to prevent surgical interventions.",
    "Jupiter (Guru)_Combust": "Donate turmeric and chana dal on Thursday. Apply a tilak of saffron on the forehead to stabilize intellect.",
    "Venus (Shukra)_Combust": "Donate pure ghee to a temple on Friday. Feed wheat dough to a cow to stabilize marital harmony.",
    "Mercury (Budh)_Combust": "Donate green moong dal on Wednesday. Clean teeth with fitkari (alum) daily to prevent nervous system burnout.",
    "Mars (Mangal)_Debilitated": "Float a piece of red copper in a flowing river on Tuesday. Sleep on a white bedsheet to calm aggressive impulses.",
    "Sun (Surya)_Debilitated": "Donate wheat and jaggery on Sunday. Offer water to the Sun (Surya Arghya) with a pinch of red sandalwood to rebuild self-worth.",
    "Moon (Chandra)_Debilitated": "Immerse a square piece of silver in a flowing river on Monday. Feed wheat flour balls to fish to cure clinical anxiety.",
    "Venus (Shukra)_Debilitated": "Donate white sweets to young girls on Friday. Keep a silver glass for drinking water to restore relationship balance.",
    "Jupiter (Guru)_Debilitated": "Water a peepal tree on Thursday. Donate yellow clothes or books to a priest or student to clear karmic debts.",
    "Saturn (Shani)_Debilitated": "Serve food to lepers or disabled people. Feed black dogs on Saturday to remove chronic structural obstacles.",
    "Saturn (Shani)_6": "Float a black mustard oil-filled bottle in a river on Saturday. Serve food to disabled people to ward off chronic debts and prolonged illnesses.",
    "Mars (Mangal)_6": "Donate red masoor dal and batasha (sweet) on Tuesday. Feed a monkey or a red dog to neutralize enemies and prevent aggressive litigation.",
    "Rahu_6": "Float a piece of lead or a black sesame oil bottle in running water on Saturday. Keep a solid silver square in the pocket to avoid deceptive litigation and maternal disputes.",
    "Ketu_6": "Donate a black and white blanket on Tuesday. Feed street dogs regularly to prevent mysterious health ailments and disputes with maternal uncles.",
    "Sun (Surya)_6": "Offer jaggery and wheat to a red cow on Sunday. Donate medicines to a hospital to prevent chronic health issues and conflicts with authorities.",
    "Saturn (Shani)_8": "Do not build a house before age 48. Drop 8 kilograms of raw coal in running water on a Saturday to prevent hospitalization.",
    "Mars (Mangal)_8": "Feed sweet bread (roti) to a red dog on Tuesday. Keep a square piece of red copper in the house to prevent sudden trauma.",
    "Rahu_8": "Keep a solid silver square piece in the pocket. Float four coconuts in a river on Saturday to mitigate sudden litigation.",
    "Ketu_8": "Donate a black and white blanket. Feed street dogs regularly to prevent genetic health complications.",
    "Sun (Surya)_8": "Offer jaggery and wheat to a red cow on Sunday. Keep a copper pot filled with water in the bedroom at night and pour it into a plant in the morning.",
    "Saturn (Shani)_12": "Keep a square piece of silver in pocket. Do not consume alcohol or non-vegetarian food on Saturdays to prevent insomnia.",
    "Mars (Mangal)_12": "Float a piece of red copper in flowing water on Tuesday. Do not keep weapons in the bedroom to prevent night terrors.",
    "Rahu_12": "Donate a black blanket to a homeless person. Keep a dog as a pet to absorb environmental malefic energy.",
    "Ketu_12": "Bury a pair of ivory pieces in a graveyard or at a crossroad. Avoid wearing fragmented or broken jewelry.",
    "Sun (Surya)_12": "Keep a copper coin in a visible spot in the house. Do not consume salt on Sundays to prevent immune system collapse."
}

def get_lal_kitab_remedy(houses_dict, planets_dict):
    remedies = []
    for p_name, p_data in planets_dict.items():
        if p_data.get("combust"):
            key = f"{p_name}_Combust"
            if key in LAL_KITAB_DICT: remedies.append(f"{p_name} is Combust: {LAL_KITAB_DICT[key]}")
        if p_data.get("dignity", "").startswith("Debilitated"):
            key = f"{p_name}_Debilitated"
            if key in LAL_KITAB_DICT: remedies.append(f"{p_name} is Debilitated: {LAL_KITAB_DICT[key]}")
                    
    for h_num in [6, 8, 12]:
        for p_name in houses_dict[h_num]["occupants"]:
            if p_name in ["Saturn (Shani)", "Mars (Mangal)", "Rahu", "Ketu", "Sun (Surya)"]:
                key = f"{p_name}_{h_num}"
                if key in LAL_KITAB_DICT: remedies.append(f"{p_name} in House {h_num}: {LAL_KITAB_DICT[key]}")
                        
    unique_remedies = list(dict.fromkeys(remedies))
    return unique_remedies[:2]

# ==========================================
# CORE BOT FUNCTIONS
# ==========================================
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
    p_chart_map = {"Sun (Surya)": chart.SUN, "Moon (Chandra)": chart.MOON, "Mars (Mangal)": chart.MARS, "Mercury (Budh)": chart.MERCURY, "Jupiter (Guru)": chart.JUPITER, "Venus (Shukra)": chart.VENUS, "Saturn (Shani)": chart.SATURN, "Rahu": chart.RAHU, "Ketu": chart.KETU}
    svg_path = f"/tmp/{filename}.svg"
    north = chart.NorthChart(title, "", IsFullChart=True)
    north.set_ascendantsign(asc_sign)
    for p_name, p_data in planets_data.items():
        if p_name in p_chart_map:
            north.add_planet(p_chart_map[p_name], p_name[:2], ZODIAC_SIGNS.index(p_data["sign"]) + 1)
    north.draw("/tmp/", filename)
    return svg_path

def draw_north_chart_drawing(asc_sign, planets_data, title="Chart"):
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
                Paragraph(f"{'Retro' if p_info['retro'] else ''} {'Combust' if p_info['combust'] else ''} {'Vargottama' if p_info.get('vargottama') else ''}", table_cell_style)
            ])
            
        planet_table = Table(table_data, colWidths=[70, 90, 110, 70, 70])
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
            
            if safe_line.startswith("# I.") or safe_line.startswith("# II.") or safe_line.startswith("# III.") or safe_line.startswith("# IV."):
                if not safe_line.startswith("# I."): story.append(PageBreak())
                story.append(Paragraph(safe_line.replace("# ", ""), h1_style))
                story.append(Spacer(1, 12))
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

def get_dasha_timeline(moon_lon, birth_dt, target_dt):
    nak_span = 360.0 / 27.0
    nak_idx, _, _, rem = get_nakshatra_info(moon_lon)
    lord_idx = (nak_idx // 3) % 9
    
    days_per_year = 365.25
    birth_jd = swe.julday(birth_dt.year, birth_dt.month, birth_dt.day)
    target_jd = swe.julday(target_dt.year, target_dt.month, target_dt.day)
    days_passed = target_jd - birth_jd
    
    m_idx = lord_idx
    m_years = (1.0 - (rem / nak_span)) * DASHA_LORDS[m_idx][1]
    is_first_maha = True
    
    while days_passed > m_years * days_per_year:
        days_passed -= m_years * days_per_year
        m_idx = (m_idx + 1) % 9
        m_years = DASHA_LORDS[m_idx][1]
        is_first_maha = False
        
    m_lord = DASHA_LORDS[m_idx][0]
    
    a_idx = m_idx
    a_years = (DASHA_LORDS[a_idx][1] * DASHA_LORDS[m_idx][1]) / 120.0
    if is_first_maha:
        a_years *= (1.0 - (rem / nak_span))
        
    while days_passed > a_years * days_per_year:
        days_passed -= a_years * days_per_year
        a_idx = (a_idx + 1) % 9
        a_years = (DASHA_LORDS[a_idx][1] * DASHA_LORDS[m_idx][1]) / 120.0
        
    current_ad = f"{m_lord}-{DASHA_LORDS[a_idx][0]}"
    
    pa_idx = a_idx
    pa_years = (DASHA_LORDS[pa_idx][1] * DASHA_LORDS[a_idx][1]) / 120.0
    pa_years *= (DASHA_LORDS[m_idx][1] / 120.0)
    
    while days_passed > pa_years * days_per_year:
        days_passed -= pa_years * days_per_year
        pa_idx = (pa_idx + 1) % 9
        pa_years = (DASHA_LORDS[pa_idx][1] * DASHA_LORDS[a_idx][1]) / 120.0
        pa_years *= (DASHA_LORDS[m_idx][1] / 120.0)
        
    current_pa = f"{DASHA_LORDS[pa_idx][0]}"
    
    if a_idx == m_idx:
        prev_m_idx = (m_idx - 1) % 9
        prev_m_lord = DASHA_LORDS[prev_m_idx][0]
        prev_a_idx = (prev_m_idx + 8) % 9 
        prev_ad = f"{prev_m_lord}-{DASHA_LORDS[prev_a_idx][0]}"
    else:
        prev_a_idx = (a_idx - 1) % 9
        prev_ad = f"{m_lord}-{DASHA_LORDS[prev_a_idx][0]}"
        
    if a_idx == (m_idx + 8) % 9:
        next_m_idx = (m_idx + 1) % 9
        next_m_lord = DASHA_LORDS[next_m_idx][0]
        next_a_idx = next_m_idx 
        next_ad = f"{next_m_lord}-{DASHA_LORDS[next_a_idx][0]}"
    else:
        next_a_idx = (a_idx + 1) % 9
        next_ad = f"{m_lord}-{DASHA_LORDS[next_a_idx][0]}"
        
    return f"Past Antardasha: {prev_ad} | Current Antardasha: {current_ad} | Future Antardasha: {next_ad} | Current Pratyantardasha: {current_ad}-{current_pa}"

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
    return [((house + a - 2) % 12) + 1 for a in aspects]

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

    fact_sheet = "[GLOBAL PLANETARY INTERCONNECTION MATRIX]\n"
    for h, data in houses.items():
        occ_str = ', '.join(data['occupants']) if data['occupants'] else 'Empty'
        asp_str = ', '.join(data['aspected_by']) if data['aspected_by'] else 'None'
        fact_sheet += f"- House {h} ({data['hindi_sign']}): Ruled by {data['ruler']}. {data['ruler']} is sitting in House {data['ruler_placed_in']}. Occupied by: {occ_str}. Aspected by: {asp_str}.\n"
    
    logic_summary = f"[LIFE STAGE FILTER - MANDATORY]: {life_stage}\n{fact_sheet}"
    
    inferences = []
    asc_lord = sign_lords.get(asc_sign)
    asc_lord_dignity = planets_full.get(asc_lord, {}).get("dignity", "Neutral")
    
    if asc_lord_dignity.startswith("Debilitated"): inferences.append("High Risk of Psychological Vitality Loss: Lagna Lord is Debilitated, structurally weakening core self-esteem and vitality.")
    if planets_full["Moon (Chandra)"]["dignity"].startswith("Debilitated"): inferences.append("High Risk of Nervous System Burnout: Moon is Debilitated, indicating chronic emotional volatility and anxiety.")
    
    if "Saturn (Shani)" in houses[2]["occupants"] and planets_full["Saturn (Shani)"]["combust"]:
        inferences.append("High Risk of Liquidity Freeze & Wealth Erosion: Saturn is Combust in the 2nd House (Wealth), severely damaging financial discipline and retention.")
        
    if houses[10]["ruler_placed_in"] in [8, 12]:
        inferences.append("High Risk of Career Collapse: 10th Lord is in the 8th or 12th House, indicating sudden career termination or structural instability.")

    yogas = detect_yogas(houses, planets_full)

    if houses[2]["ruler_placed_in"] in [6, 8, 12] or houses[11]["ruler_placed_in"] in [6, 8, 12]:
        yogas.append("Daridra Yoga (Poverty Yoga): 2nd or 11th Lord is in a Dusthana (6/8/12). This confirms the structural root of the liquidity freeze and severe wealth erosion.")

    for p_name in ["Mars (Mangal)", "Mercury (Budh)", "Jupiter (Guru)", "Venus (Shukra)", "Saturn (Shani)"]:
        if p_name in planets_full:
            p_house = get_house_of_planet(houses, p_name)
            p_dignity = planets_full[p_name]["dignity"]
            if p_house in [1, 4, 7, 10] and ("Own Sign" in p_dignity or "Exalted" in p_dignity):
                yogas.append(f"Panch Mahapurusha Yoga ({p_name.split(' ')[0]} in Kendra): Exceptional potential in its domain, but requires harnessing amidst the current crisis.")

    lal_kitab_rules = get_lal_kitab_remedy(houses, planets_full)
    
    logic_summary += f"\n[PRE-CALCULATED YOGAS]:\n - " + "\n - ".join(yogas) if yogas else "\n[PRE-CALCULATED YOGAS]: None."
    logic_summary += f"\n[HARD DEDUCTIVE INFERENCES]:\n - " + "\n - ".join(inferences) if inferences else "\n[HARD DEDUCTIVE INFERENCES]: None."
    logic_summary += f"\n[MANDATORY LAL KITAB REMEDY]:\n - " + "\n - ".join(lal_kitab_rules) if lal_kitab_rules else "\n[MANDATORY LAL KITAB REMEDY]: None."

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
        if name == "Ketu": 
            lon_val = (rahu_lon + 180.0) % 360.0; speed = 0
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
        nak_idx, nak_name, pada, _ = get_nakshatra_info(lon_val)
        nak_lord = get_nakshatra_lord(nak_idx) 
        
        dignity = get_planet_dignity(name, sign_name)
        is_retro = speed < 0 if name not in ["Sun (Surya)", "Moon (Chandra)"] else False
        is_combust = False
        if name in COMBUSTION_ORB:
            dist_to_sun = abs(lon_val - sun_lon)
            if dist_to_sun > 180: dist_to_sun = 360 - dist_to_sun
            if dist_to_sun < COMBUSTION_ORB[name]: is_combust = True
            
        d9_sign_idx = int((lon_val % (30/9)) / (30/9)) + (sign_idx * 9); d9_sign_name = ZODIAC_SIGNS[d9_sign_idx % 12]
        is_vargottama = (sign_name == d9_sign_name)
        
        positions[name] = {
            "sign": sign_name, "hindi_sign": HINDI_SIGNS[sign_name], "lon": lon_val % 360.0, 
            "nak": nak_name, "nak_lord": nak_lord, "pada": pada, 
            "dignity": dignity, "retro": is_retro, "combust": is_combust, 
            "vargottama": is_vargottama, "jaimini": ""
        }
        d9_positions[name] = {"sign": d9_sign_name, "hindi_sign": HINDI_SIGNS[d9_sign_name]}
        
    try: 
        _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags); asc_lon = ascmc[0] % 360.0
    except: 
        asc_lon = 0.0
        
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]; _, asc_nak, asc_pada, _ = get_nakshatra_info(asc_lon)
    asc_d9_sign_idx = int((asc_lon % (30/9)) / (30/9)) + (ZODIAC_SIGNS.index(asc_sign) * 9); asc_d9_sign = ZODIAC_SIGNS[asc_d9_sign_idx % 12]
    
    # --- JAIMINI KARAKAS CALCULATION ---
    jaimini_planets = []
    for name in ["Sun (Surya)", "Moon (Chandra)", "Mars (Mangal)", "Mercury (Budh)", "Jupiter (Guru)", "Venus (Shukra)", "Saturn (Shani)"]:
        if name in positions:
            deg_in_sign = positions[name]["lon"] % 30
            jaimini_planets.append((name, deg_in_sign))
            
    jaimini_planets.sort(key=lambda x: x[1], reverse=True)
    
    if len(jaimini_planets) >= 1:
        positions[jaimini_planets[0][0]]["jaimini"] = "Atmakaraka (Soul's Core Karma)"
    if len(jaimini_planets) >= 2:
        positions[jaimini_planets[1][0]]["jaimini"] = "Amatyakaraka (Career & Wealth Driver)"
    
    now_dt = datetime.now()
    dasha_timeline = get_dasha_timeline(moon_lon, dt_ist, now_dt)
    
    t_ctx = {
        "current_date": now_dt.strftime("%B %d, %Y"), 
        "dasha_timeline": dasha_timeline, 
        "asc_nakshatra": f"{asc_nak} Pada {asc_pada}"
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

def llm_output_firewall(text, logic_summary):
    none_houses = re.findall(r"House (\d+).*?Aspected by: none\.", logic_summary, re.IGNORECASE)
    clean_text = text
    for h_num in none_houses:
        pattern = rf'(?i)([^.]*aspect[^.]*House {h_num}[^.]*\.)|([^.]House {h_num}[^.]*aspect[^.]*\.)'
        def replace_func(match):
            if "no planetary" in match.group(0).lower() or "none" in match.group(0).lower():
                return match.group(0)
            return " [REDACTED BY SYSTEM GUARD: HALLUCINATED ASPECT] "
        clean_text = re.sub(pattern, replace_func, clean_text)
    return clean_text

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
                
            match = re.search(r'^(?:(?P<name>[A-Za-z][\w\s\.]+?)\s+)?(?P<day>\d{1,2})\s*[-/]\s*(?P<month>\d{1,2})\s*[-/]\s*(?P<year>\d{2,4})\s+(?P<hour>\d{1,2}):(?P<minute>\d{1,2})\s+(?P<city>[A-Za-z][\w\s\(\)\&\-]+)$', user_text)
            
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
                
                # UPDATED planet_summary LOGIC WITH NAK LORDS & JAIMINI
                planet_summary = "\n".join([
                    f"- {p}: {d['hindi_sign']} | Nak: {d['nak']} (ruled by {d.get('nak_lord', 'Unknown')}) | Dignity: {d['dignity']} {'[Vargottama]' if d.get('vargottama') else ''} | {d['jaimini']}" 
                    if d.get('jaimini') else 
                    f"- {p}: {d['hindi_sign']} | Nak: {d['nak']} (ruled by {d.get('nak_lord', 'Unknown')}) | Dignity: {d['dignity']} {'[Vargottama]' if d.get('vargottama') else ''}" 
                    for p, d in planets.items()
                ])
                
                USER_SESSIONS[chat_id] = {
                    "state": "awaiting_focus",
                    "asc_sign": asc_sign, "planet_summary": planet_summary,
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
    
    system_msg = """You are an Elite Forensic Astrological Diagnostician. You write tactical, highly structured threat-matrix dossiers. 
[ABSOLUTE LAWS - VIOLATION = FAILURE]
1. FORBIDDEN PHRASES: Do not use 'manage stress', 'practice mindfulness', 'seek balance', 'self-care', 'Assuming', 'Potentially', 'possibly', or 'suggesting'. Use blunt, definitive diagnostic statements.
2. CHAIN OF DEDUCTION: For every Threat Vector, you MUST output your analysis in this exact 4-part structure:
   - Astronomical Root: [State the hard planet/house/nakshatra data]
   - Systemic Vulnerability: [Explain the structural/neurological weakness this creates]
   - Real-World Manifestation: [State exactly what this looks like in the user's daily life, career, or bank account]
   - Tactical Countermeasure: [Provide the prescribed remedy]
3. THE PUPPET MASTERS: You must analyze the Nakshatra Lords. A planet is only as strong as its Nakshatra Lord. 
4. JAIMINI MANDATE: You must explicitly interpret the Atmakaraka (Soul's Core Karma) and Amatyakaraka (Career Driver). 
5. LAL KITAB STRICTNESS: Use the exact remedies provided in the [MANDATORY LAL KITAB REMEDY] section verbatim. Do not invent remedies.
6. HINDI MANDATORY: Use the Hindi names provided for EVERY Zodiac Sign and Planet.
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
- Ascendant Nakshatra: {session['t_ctx']['asc_nakshatra']}
- Exact Dasha Timeline: {session['t_ctx']['dasha_timeline']}
{session['logic_breakdown']}

[USER FOCUS AREAS]: {session['focus_areas']}

[PLANETARY ARRAY]
- Ascendant (Lagna): {HINDI_SIGNS[session['asc_sign']]}
{session['planet_summary']}

[OUTPUT TEMPLATE - FOLLOW EXACTLY]
*Disclaimer: This audit maps karmic tendencies and probabilistic risk vectors based on planetary mathematics. Astrological indications are environmental influences, not absolute mandates.*

# I. EXECUTIVE DIAGNOSIS (The Karmic Baseline)
- **The Core Constraint (Atmakaraka):** Explicitly name the Atmakaraka planet. Diagnose the native's primary, inescapable karmic loop and psychological bottleneck based on this planet.
- **The Structural Reality:** Write a brutal synthesis of the [PRE-CALCULATED YOGAS] and [HARD DEDUCTIVE INFERENCES]. State the absolute truth of their current crisis.

# II. THE TEMPORAL TRIGGER (Micro-Timing)
- **Current Pratyantardasha Trigger:** Analyze the Current Pratyantardasha. Look at the Dasha Lord and its Nakshatra Lord. Explain exactly *why* the financial/psychological collapse triggered right now.
- **Timeline Trajectory:** Briefly contrast this with the Past Antardasha and define the survival requirements for the Future Antardasha.

# III. THREAT MATRIX & DEDUCTIVE TRIAGE
*(Analyze the following vectors using the strict 4-part Chain of Deduction)*

**Vector 1: Wealth, Career & Amatyakaraka**
- [FACT BLOCKS]: House 2: {h2_facts} | House 10: {h10_facts} | House 11: {h11_facts}
- **Astronomical Root:** (State the specific planetary dignities, Amatyakaraka, and empty/aspected houses)
- **Systemic Vulnerability:** (Explain the mechanical flaw in their wealth generation or career structure)
- **Real-World Manifestation:** (Diagnose the liquidity freeze, business shutdown, or career stagnation bluntly)
- **Tactical Countermeasure:** (Provide the exact [MANDATORY LAL KITAB REMEDY] verbatim here, plus 1 tactical non-astrological financial step)

**Vector 2: Neurological & Psychological Baseline**
- [FACT BLOCKS]: House 6: {h6_facts} | House 8: {h8_facts} | House 12: {h12_facts}
- **Astronomical Root:** (State the Moon's dignity, Nakshatra Lord, and Dosha)
- **Systemic Vulnerability:** (Explain the exact neurological breakdown, e.g., Vata/Pitta overload)
- **Real-World Manifestation:** (Diagnose clinical anxiety, panic, or insomnia)
- **Tactical Countermeasure:** (Specific dietary/lifestyle shifts for their Dosha, plus 1-2 specific gemstones with exact metal, finger, and day)

**Vector 3: Relationship & Partnership Dynamics**
- [FACT BLOCKS]: House 7: {h7_facts}
- **Astronomical Root:** (State the 7th house occupants and aspects)
- **Systemic Vulnerability:** (Explain the psychological friction or emotional unavailability)
- **Real-World Manifestation:** (State how this damages their marriage or business partnerships)
- **Tactical Countermeasure:** (Specific behavioral adjustment)

# IV. LONG-TERM ALIGNMENT STRATEGY
- Detail specific Mantras for the Lagna Lord or afflicted planets to rebuild self-worth and survive the upcoming Future Dasha.
{synastry_block}
"""

    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}], "temperature": 0.3}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
    res = requests.post(groq_url, headers=headers, json=payload, timeout=120)
    
    if res.status_code == 200:
        final_text = res.json()['choices'][0]['message']['content']
        
        # POST-GENERATION PYTHON FIREWALL
        final_text = llm_output_firewall(final_text, logic)
        
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
