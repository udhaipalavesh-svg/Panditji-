# ==========================================
# THE CELESTIAL STRATEGY DOSSIER - MAIN CORE
# ==========================================
import os, requests, re, time, sqlite3, threading, json, markdown2
from weasyprint import HTML
from datetime import datetime, timedelta
import swisseph as swe
from flask import Flask, request, jsonify

# IMPORT THE UNCOMPRESSED DATA WAREHOUSE
from astro_data import *

app = Flask(__name__)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
DB_PATH = os.environ.get("DB_PATH", "/tmp/bot.db")

# ==========================================
# DATABASE MANAGER (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (chat_id INTEGER PRIMARY KEY, session_data TEXT)''')
    conn.commit()
    conn.close()

def save_session(chat_id, data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO sessions (chat_id, session_data) VALUES (?, ?)", (chat_id, json.dumps(data)))
    conn.commit()
    conn.close()

def get_session(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT session_data FROM sessions WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def clear_session(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

# ==========================================
# MATHEMATICAL ENGINE (SWISSEPH)
# ==========================================
def get_planet_dignity(planet, sign):
    if EXALTATION.get(planet) == sign: return "Exalted / Uchcha"
    if DEBILITATION.get(planet) == sign: return "Debilitated / Neecha"
    if planet in OWN_SIGNS and sign in OWN_SIGNS[planet]: return "Own Sign / Swavritti"
    return "Neutral"

def get_aspects(planet, house):
    aspects = [7]
    if "Mars" in planet: aspects.extend([4, 8])
    elif "Jupiter" in planet: aspects.extend([5, 9])
    elif "Saturn" in planet: aspects.extend([3, 10])
    elif "Rahu" in planet or "Ketu" in planet: aspects.extend([5, 9])
    return [((house + a - 2) % 12) + 1 for a in aspects]

def calculate_bav(planet_name, target_house, houses_dict):
    if planet_name not in BAV_TABLES: return 0
    p_house = next((h for h, d in houses_dict.items() if planet_name in d["occupants"]), None)
    if not p_house: return 0
    start_idx = (((target_house - p_house) % 12)) * 8
    return sum(BAV_TABLES[planet_name][start_idx : start_idx + 8])

def calculate_full_sav(houses_dict):
    planets_for_sav = ["Sun / Surya", "Moon / Chandra", "Mars / Mangal", "Mercury / Budh", "Jupiter / Guru", "Venus / Shukra", "Saturn / Shani"]
    return {h: sum(calculate_bav(p, h, houses_dict) for p in planets_for_sav) for h in range(1, 13)}

def calculate_vargas(natal_planets_dict):
    vargas = {}
    navamsha_start_map = [0, 9, 6, 3] 
    for planet, data in natal_planets_dict.items():
        lon = data.get("lon", 0.0) % 360.0
        sign_idx = int(lon // 30) % 12
        deg_in_sign = lon % 30
        d9_sign_idx = (navamsha_start_map[sign_idx % 4] + int(deg_in_sign // (30/9))) % 12
        d10_sign_idx = (sign_idx + (0 if sign_idx % 2 == 0 else 8) + int(deg_in_sign // 3)) % 12
        vargas[planet] = {"D9": ZODIAC_SIGNS[d9_sign_idx], "D10": ZODIAC_SIGNS[d10_sign_idx]}
    return vargas

def detect_yogas(houses_dict, planets_dict):
    yogas = []
    moon_house = next((h for h, d in houses_dict.items() if "Moon / Chandra" in d["occupants"]), None)
    jup_house = next((h for h, d in houses_dict.items() if "Jupiter / Guru" in d["occupants"]), None)
    if moon_house and jup_house and abs(jup_house - moon_house) in [0, 3, 6, 9]:
        yogas.append("Gaja Kesari Yoga (Jupiter in Kendra from Moon): Indicates intellectual capacity, reputation, and leadership.")
    return yogas

def calculate_vimshottari_timeline(moon_lon, birth_dt_iso):
    birth_dt = datetime.fromisoformat(birth_dt_iso)
    nak_span = 360.0 / 27.0
    nak_idx = int(moon_lon / nak_span) % 27
    lord_idx = (nak_idx // 3) % 9
    rem = moon_lon % nak_span
    fraction_remaining = 1.0 - (rem / nak_span)
    birth_jd = swe.julday(birth_dt.year, birth_dt.month, birth_dt.day)
    now_jd = swe.julday(datetime.now().year, datetime.now().month, datetime.now().day)
    
    curr_m_idx = lord_idx
    curr_m_start_jd = birth_jd
    curr_m_years = DASHA_LORDS[curr_m_idx][1] * fraction_remaining
    timeline = []
    while True:
        curr_m_end_jd = curr_m_start_jd + (curr_m_years * 365.25)
        if curr_m_end_jd > now_jd:
            m_lord = DASHA_LORDS[curr_m_idx][0]
            a_idx = curr_m_idx
            a_years = (DASHA_LORDS[a_idx][1] * DASHA_LORDS[curr_m_idx][1]) / 120.0
            if curr_m_idx == lord_idx: a_years *= fraction_remaining
            a_start_jd = curr_m_start_jd
            
            periods_found = 0
            while periods_found < 4:
                a_end_jd = a_start_jd + (a_years * 365.25)
                if a_end_jd > now_jd or periods_found > 0:
                    a_lord = DASHA_LORDS[a_idx][0]
                    sy, sm, sd = swe.revjul(a_start_jd)[:3]
                    ey, em, ed = swe.revjul(a_end_jd)[:3]
                    phase_name = "Current Phase" if periods_found == 0 else f"Phase {periods_found+1}"
                    timeline.append((phase_name, f"{m_lord} — {a_lord}", f"{int(sm):02d}/{int(sy)}", f"{int(em):02d}/{int(ey)}"))
                    periods_found += 1
                
                a_start_jd = a_end_jd
                a_idx = (a_idx + 1) % 9
                a_years = (DASHA_LORDS[a_idx][1] * DASHA_LORDS[curr_m_idx][1]) / 120.0
            break
        curr_m_start_jd = curr_m_end_jd
        curr_m_idx = (curr_m_idx + 1) % 9
        curr_m_years = DASHA_LORDS[curr_m_idx][1]
    return timeline

def calculate_transit_timings():
    now_dt = datetime.now()
    swe.set_ephe_path(None); swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    dt_utc = now_dt - timedelta(hours=5, minutes=30)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0)
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    
    planets_to_track = {"Saturn / Shani": swe.SATURN, "Jupiter / Guru": swe.JUPITER, "Rahu / Rahu": swe.MEAN_NODE}
    timings = []
    for name, p_id in planets_to_track.items():
        calc = swe.calc_ut(jdut, p_id, flags)
        curr_sign = int((calc[0][0] if isinstance(calc[0], tuple) else calc[0]) / 30) % 12
        scan_jd = jdut
        for _ in range(730):
            scan_jd += 1.0
            calc_scan = swe.calc_ut(scan_jd, p_id, flags)
            scan_sign = int((calc_scan[0][0] if isinstance(calc_scan[0], tuple) else calc_scan[0]) / 30) % 12
            if scan_sign != curr_sign:
                ingress_date = swe.revjul(scan_jd)
                timings.append(f"{name} enters {ZODIAC_SIGNS[scan_sign]} on {ingress_date[1]:02d}/{ingress_date[0]}")
                break
    return "; ".join(timings) if timings else "No major ingress in next 2 years"

def calculate_sidereal_chart(day, month, year, hour, minute, lat, lon):
    swe.set_ephe_path(None); swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    dt_ist = datetime(year, month, day, hour, minute)
    dt_utc = dt_ist - timedelta(hours=5, minutes=30)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + (dt_utc.minute / 60.0))
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    
    planets = {"Sun / Surya": swe.SUN, "Moon / Chandra": swe.MOON, "Mars / Mangal": swe.MARS, "Mercury / Budh": swe.MERCURY, "Jupiter / Guru": swe.JUPITER, "Venus / Shukra": swe.VENUS, "Saturn / Shani": swe.SATURN, "Rahu / Rahu": swe.MEAN_NODE, "Ketu / Ketu": 10}
    positions = {}; rahu_lon = 0.0; sun_lon = 0.0
    
    for name, p_id in planets.items():
        if name == "Ketu / Ketu": lon_val = (rahu_lon + 180.0) % 360.0
        else:
            calc = swe.calc_ut(jdut, p_id, flags)
            lon_val = calc[0][0] if isinstance(calc, tuple) and isinstance(calc[0], tuple) else (calc[0] if isinstance(calc, tuple) else 0.0)
            if name == "Rahu / Rahu": rahu_lon = lon_val
            if name == "Sun / Surya": sun_lon = lon_val
            
        sign_idx = int(lon_val / 30) % 12; sign_name = ZODIAC_SIGNS[sign_idx]
        nak_idx = int(lon_val / (360.0 / 27.0)) % 27
        positions[name] = {
            "sign": sign_name, "hindi_sign": HINDI_SIGNS[sign_name], "lon": lon_val % 360.0, 
            "nak": NAKSHATRAS[nak_idx], "dignity": get_planet_dignity(name, sign_name),
            "combust": (abs(lon_val - sun_lon) < COMBUSTION_ORB.get(name, 0)) if name in COMBUSTION_ORB else False
        }
        
    try: _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags); asc_lon = ascmc[0] % 360.0
    except: asc_lon = 0.0
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]
    
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    houses = {i+1: {"sign": ZODIAC_SIGNS[(asc_idx + i) % 12], "occupants": [], "aspected_by": []} for i in range(12)}
    for p_name, p_data in positions.items():
        for h_num, h_data in houses.items():
            if h_data["sign"] == p_data["sign"]: h_data["occupants"].append(p_name); break
    for p_name, p_data in positions.items():
        occ_h = next((h for h, d in houses.items() if p_name in d["occupants"]), None)
        if occ_h:
            for ah in get_aspects(p_name, occ_h): houses[ah]["aspected_by"].append(p_name)
            
    vargas = calculate_vargas(positions)
    sav = calculate_full_sav(houses)
    yogas = detect_yogas(houses, positions)
    
    logic_summary = f"[VARGAS]: {json.dumps(vargas)}\n[SAV]: {json.dumps(sav)}\n[YOGAS]: {json.dumps(yogas)}\n[TRANSITS]: {calculate_transit_timings()}\n"
    logic_summary += "\n".join([f"- H{h} ({d['sign']}): Occ: {','.join(d['occupants'])}. Asp: {','.join(d['aspected_by'])}." for h, d in houses.items()])
    return asc_sign, positions, houses, sav, logic_summary, dt_ist.isoformat()

def get_applicable_remedies(houses_dict, planet_data):
    remedies = []
    for p_name, p_data in planet_data.items():
        if p_data.get("combust") and f"{p_name}_Combust" in LAL_KITAB_DICT: remedies.append(f"{p_name} Combust: {LAL_KITAB_DICT[f'{p_name}_Combust']}")
        if p_data.get("dignity", "").startswith("Debilitated") and f"{p_name}_Debilitated" in LAL_KITAB_DICT: remedies.append(f"{p_name} Debilitated: {LAL_KITAB_DICT[f'{p_name}_Debilitated']}")
    for h_num, data in houses_dict.items():
        for p_name in data["occupants"]:
            if f"{p_name}_{h_num}" in LAL_KITAB_DICT: remedies.append(f"{p_name} in H{h_num}: {LAL_KITAB_DICT[f'{p_name}_{h_num}']}")
    return list(dict.fromkeys(remedies))

# ==========================================
# NATIVE PYTHON HTML & SVG CONSTRUCTORS
# ==========================================
def generate_ephemeris_table_html(planet_positions):
    html = '<table class="data-table"><tr><th>Planet / Graha</th><th>Sign</th><th>Degree</th><th>Nakshatra</th><th>Condition</th></tr>'
    for p_name, data in planet_positions.items():
        deg = f"{int(data['lon'] % 30)}° {int((data['lon'] % 1) * 60)}'"
        cond = [data['dignity'].split('/')[0].strip()] if data['dignity'] != "Neutral" else []
        if data.get('combust'): cond.append("Combust")
        cond_str = ", ".join(cond) if cond else "Neutral"
        html += f"<tr><td><strong>{p_name}</strong></td><td>{data['sign']}</td><td>{deg}</td><td>{data['nak']}</td><td>{cond_str}</td></tr>"
    html += '</table>'
    return html

def generate_dasha_table_html(timeline_data):
    html = '<table class="data-table"><tr><th>Phase</th><th>Ruling Lords</th><th>Start Date</th><th>End Date</th></tr>'
    for row in timeline_data:
        html += f"<tr><td><strong>{row[0]}</strong></td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td></tr>"
    html += "</table>"
    return html

def generate_mantra_table_html(planet_data, asc_sign):
    sign_lords = {"Aries": "Mars / Mangal", "Taurus": "Venus / Shukra", "Gemini": "Mercury / Budh", "Cancer": "Moon / Chandra", "Leo": "Sun / Surya", "Virgo": "Mercury / Budh", "Libra": "Venus / Shukra", "Scorpio": "Mars / Mangal", "Sagittarius": "Jupiter / Guru", "Capricorn": "Saturn / Shani", "Aquarius": "Saturn / Shani", "Pisces": "Jupiter / Guru"}
    asc_lord = sign_lords.get(asc_sign)

    targets = set()
    if asc_lord: targets.add(asc_lord)
    for p, d in planet_data.items():
        if d.get('combust') or d.get('dignity', '').startswith('Debilitated') or 'Rahu' in p or 'Ketu' in p:
            targets.add(p)

    html = '<table class="data-table"><tr><th>Afflicted / Key Planet</th><th>Vedic Beej Mantra (Chant 108x)</th><th>Traditional Spiritual Upaya</th></tr>'
    for p in targets:
        if p in VEDIC_MANTRAS:
            html += f"<tr><td><strong>{p}</strong></td><td><em>{VEDIC_MANTRAS[p]}</em></td><td>{VEDIC_UPAYAS[p]}</td></tr>"
    html += "</table>"
    return html

def generate_remedies_table_html(remedies_list):
    html = '<table class="data-table"><tr><th>Karmic Friction</th><th>Lal Kitab Behavioral Protocol</th><th style="width: 50px; text-align:center;">Done</th></tr>'
    if not remedies_list:
        html += '<tr><td colspan="3">No major structural Lal Kitab afflictions detected. Maintain general grounding practices.</td></tr>'
    else:
        for r in remedies_list:
            parts = r.split(':')
            if len(parts) == 2:
                html += f"<tr><td><strong>{parts[0].strip()}</strong></td><td>{parts[1].strip()}</td><td style='text-align:center;'><div style='width:16px; height:16px; border:1px solid #101827; border-radius:2px; margin:auto;'></div></td></tr>"
    html += "</table>"
    return html

def get_sacred_svg_symbols():
    # PURE VECTOR PATHS - Immunity to missing fonts on Cloud Servers
    return """
    <g transform="translate(320, 200) scale(0.6)">
        <!-- Vector Om -->
        <path d="M42.2,46.1c-2.4,0-5.7-0.9-8.4-3.1c-2.7-2.3-4.6-5.8-4.6-10.4c0-5.2,2.4-9.3,5.6-11.8 c3-2.3,6.8-3.4,9.6-3.4c5.8,0,10.6,2.8,13.2,7.3c0.9,1.6,1.4,3.3,1.4,5c0,3.6-2.1,6.8-5.3,8.5v0.2c4.1,1.1,7.2,4.8,7.2,9.3 c0,2.1-0.6,4.3-1.8,6.2c-2.9,4.8-8.6,8.2-15.5,8.2c-5.2,0-10.2-1.9-13.6-5c-2.8-2.5-4.5-6-4.5-9.6c0-2.2,0.6-4.4,1.8-6.1 c0.9-1.4,2.2-2.5,3.7-3.2l2.3,4.4c-0.9,0.5-1.5,1.2-2,2.1c-0.7,1.1-1.1,2.5-1.1,4c0,2.4,1.2,4.7,3.1,6.4c2.4,2.1,6.1,3.4,9.9,3.4 c5,0,9.3-2.4,11.3-5.8c0.8-1.3,1.2-2.8,1.2-4.3c0-3.1-2-5.9-5.1-7.2l-3.3-1.4v-4.8l2.9-1.1c2.6-1.1,4.4-3.5,4.4-6.3 c0-1.2-0.3-2.4-0.9-3.5c-1.8-3.2-5.4-5.2-9.7-5.2c-2.1,0-4.8,0.8-6.9,2.4c-2.2,1.7-3.8,4.5-3.8,8.2c0,3.1,1.2,5.5,3.1,7.1 c1.8,1.5,4,2.2,5.6,2.2l0.2,4.9H42.2z M80.5,23.3c-2.2-3.1-6-5.2-10.4-5.2c-5,0-9.2,2.4-11.4,5.9l4.2,2.6c1.5-2.2,4.2-3.8,7.4-3.8 c3,0,5.5,1.3,7,3.4L80.5,23.3z M71.6,12.7c-2.1,0-3.8-1.7-3.8-3.8s1.7-3.8,3.8-3.8s3.8,1.7,3.8,3.8S73.7,12.7,71.6,12.7z" fill="#B68A3A"/>
        <!-- Vector Swastik -->
        <g transform="translate(100, 5)" stroke="#B68A3A" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path d="M 40,10 L 40,50 L 90,50" />
            <path d="M 10,50 L 60,50 L 60,90" />
            <path d="M 60,10 L 60,50" />
            <path d="M 40,50 L 40,90" />
            <circle cx="25" cy="25" r="2" fill="#B68A3A" stroke="none"/>
            <circle cx="75" cy="25" r="2" fill="#B68A3A" stroke="none"/>
            <circle cx="25" cy="75" r="2" fill="#B68A3A" stroke="none"/>
            <circle cx="75" cy="75" r="2" fill="#B68A3A" stroke="none"/>
        </g>
    </g>
    """

def generate_cover_page_svg(native_name="Confidential Dossier", birth_str=""):
    sacred_symbols = get_sacred_svg_symbols()
    return f"""
    <svg viewBox="0 0 800 1130" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: 100vh; font-family: 'Georgia', serif;">
        <rect width="800" height="1130" fill="#101827" />
        <rect x="40" y="40" width="720" height="1050" fill="none" stroke="#B68A3A" stroke-width="1" />
        <circle cx="400" cy="565" r="300" fill="none" stroke="#B68A3A" stroke-width="0.5" stroke-dasharray="4,8" opacity="0.4"/>
        <circle cx="400" cy="565" r="200" fill="none" stroke="#B68A3A" stroke-width="0.5" stroke-dasharray="2,4" opacity="0.3"/>
        
        {sacred_symbols}
        
        <text x="400" y="420" font-size="28" fill="#F5F0E6" text-anchor="middle" font-weight="300" letter-spacing="4">THE CELESTIAL STRATEGY</text>
        <text x="400" y="480" font-size="48" fill="#B68A3A" text-anchor="middle" font-weight="bold" letter-spacing="6">DOSSIER</text>
        
        <line x1="300" y1="520" x2="500" y2="520" stroke="#B68A3A" stroke-width="1"/>
        <text x="400" y="560" font-size="12" fill="#71866B" text-anchor="middle" letter-spacing="2" font-family="'Helvetica', sans-serif;">NATAL ARCHITECTURE • LIFE THEMES • TIMING MAP</text>
        
        <text x="400" y="800" font-size="12" fill="#F5F0E6" text-anchor="middle" letter-spacing="1" font-family="'Helvetica', sans-serif;">PREPARED FOR</text>
        <text x="400" y="830" font-size="18" fill="#B68A3A" text-anchor="middle" font-weight="bold" letter-spacing="2">{native_name}</text>
        <text x="400" y="860" font-size="12" fill="#71866B" text-anchor="middle" font-family="'Helvetica', sans-serif;">{birth_str}</text>
        
        <text x="400" y="1050" font-size="10" fill="#71866B" text-anchor="middle" font-family="'Helvetica', sans-serif;">An objective Vedic-astrology and strategic executive report.</text>
    </svg>
    """

def generate_rasi_chart_svg(planet_positions, asc_sign):
    width = 400; height = 400
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    h_coords = {
        1: (200, 100), 2: (100, 50), 3: (50, 100), 4: (100, 200),
        5: (50, 300), 6: (100, 350), 7: (200, 300), 8: (300, 350),
        9: (350, 300), 10: (300, 200), 11: (350, 100), 12: (300, 50)
    }
    house_planets = {i: [] for i in range(1, 13)}
    for p_name, data in planet_positions.items():
        p_sign_idx = ZODIAC_SIGNS.index(data["sign"])
        h_num = ((p_sign_idx - asc_idx + 12) % 12) + 1
        abbr = p_name.split("/")[0].strip()[:2]
        house_planets[h_num].append(abbr)
        
    svg = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; font-family: Helvetica, sans-serif;">',
        '<rect x="0" y="0" width="400" height="400" fill="#F5F0E6" stroke="#101827" stroke-width="2"/>',
        '<polygon points="200,0 400,200 200,400 0,200" fill="none" stroke="#101827" stroke-width="1.5"/>',
        '<line x1="0" y1="0" x2="400" y2="400" stroke="#101827" stroke-width="1"/>',
        '<line x1="400" y1="0" x2="0" y2="400" stroke="#101827" stroke-width="1"/>',
        '<line x1="0" y1="200" x2="400" y2="200" stroke="#101827" stroke-width="1"/>',
        '<line x1="200" y1="0" x2="200" y2="400" stroke="#101827" stroke-width="1"/>'
    ]
    for h_num, (x, y) in h_coords.items():
        sign_num = ((asc_idx + h_num - 1) % 12) + 1
        svg.append(f'<text x="{x}" y="{y-12}" font-size="10" fill="#71866B" text-anchor="middle">{sign_num}</text>')
        if house_planets[h_num]:
            svg.append(f'<text x="{x}" y="{y+8}" font-size="11" font-weight="bold" fill="#101827" text-anchor="middle">{", ".join(house_planets[h_num])}</text>')
    svg.append('</svg>')
    return "\n".join(svg)

def generate_sav_heatmap_svg(sav_dict):
    width = 600; height = 250; margin_top = 30; margin_bottom = 45
    chart_height = height - margin_top - margin_bottom; y_scale = chart_height / 50 
    baseline_y = height - margin_bottom - (28 * y_scale)
    
    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; font-family: sans-serif;">',
        '<rect width="100%" height="100%" fill="#F5F0E6" rx="4" />',
        f'<line x1="30" y1="{baseline_y:.2f}" x2="{width-30}" y2="{baseline_y:.2f}" stroke="#B68A3A" stroke-width="1.5" stroke-dasharray="4,4" />',
        f'<text x="{width-35}" y="{baseline_y-6:.2f}" font-size="9" fill="#B68A3A" text-anchor="end" font-weight="bold">Karmic Baseline (28)</text>'
    ]
    for i in range(1, 13):
        score = sav_dict.get(i, 0)
        bar_height = max(0, min(score, 50)) * y_scale
        x = 35 + ((i - 1) * 44); y = height - margin_bottom - bar_height
        color = "#71866B" if score >= 28 else "#A95D45"
        svg_parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="34" height="{bar_height:.2f}" fill="{color}" rx="2" ry="2" />')
        svg_parts.append(f'<text x="{x + 17:.2f}" y="{y - 5:.2f}" font-size="10" font-weight="bold" fill="#101827" text-anchor="middle">{score}</text>')
        svg_parts.append(f'<text x="{x + 17:.2f}" y="{height - margin_bottom + 18}" font-size="10" fill="#71866B" text-anchor="middle">H{i}</text>')
    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

# ==========================================
# LLM ORCHESTRATION & PDF ENGINE
# ==========================================
def generate_pdf_weasyprint(html_content, pdf_path):
    try: HTML(string=html_content).write_pdf(pdf_path); return True
    except Exception as e: print(f"PDF ERROR: {e}", flush=True); return False

def send_message(chat_id, text):
    try: requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except: pass

def send_document(chat_id, file_path):
    try:
        with open(file_path, 'rb') as f: requests.post(f"{TELEGRAM_API_URL}/sendDocument", data={'chat_id': chat_id}, files={'document': f}, timeout=30)
    except: pass

def call_groq_agent(system_prompt, user_prompt, models_list):
    groq_key = os.environ.get("GROQ_API_KEY")
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    payload_base = {"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.2}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
    
    for model_name in models_list:
        payload = payload_base.copy(); payload["model"] = model_name
        for attempt in range(2):
            try:
                res = requests.post(groq_url, headers=headers, json=payload, timeout=180)
                if res.status_code == 200: return res.json()['choices'][0]['message']['content']
                elif res.status_code == 429: time.sleep(20); continue
                else: break
            except: break
    return '{"error": "Failed"}'

def process_background_task(chat_id, session_data):
    MASTER_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "groq/compound"]
    send_message(chat_id, "⏳ Compiling The Celestial Strategy Dossier (Dialectic Build)...")

    # THE DIALECTIC PROMPT (Curing the Fatalism & Wall of Text)
    base_cognitive_rules = """You are an Elite Executive Astrological Advisor.
    [DIALECTIC LAWS]
    1. OBJECTIVITY: Do not sugarcoat, but do not be fatalistic. Frame negative traits as 'Strategic Vulnerabilities' to be managed, not character condemnations.
    2. THE BRIDGE: You will be provided with specific physical remedies (Lal Kitab). You MUST weave the psychological rationale for these physical remedies into your 'Executive Pivot' advice.
    3. FORMATTING: You must output a RAW JSON object with EXACTLY three keys: "asset", "vulnerability", and "executive_pivot". The values must use HTML bullet points (<ul><li>) and bold tags (<b>) for scannability. NO long paragraphs. NO markdown."""

    remedies_text = " | ".join(session_data['remedies'])
    base_user_msg = f"Ascendant: {session_data['asc_sign']}\nData: {session_data['logic_breakdown']}\nPRESCRIBED REMEDIES TO EXPLAIN: {remedies_text}"

    swarm_chapters = {
        "psychology": base_cognitive_rules + "\nAnalyze the native's psychological operating system and cognitive drive. Output JSON with 'asset', 'vulnerability', and 'executive_pivot'.",
        "career_wealth": base_cognitive_rules + "\nAnalyze career apex and wealth potential based on D-10 and Yogas. Output JSON with 'asset', 'vulnerability' (blind spots/risks), and 'executive_pivot'.",
        "relational_karma": base_cognitive_rules + "\nAnalyze relationship karma based on D-9 Navamsha. Output JSON with 'asset', 'vulnerability' (intimacy constraints), and 'executive_pivot'.",
        "ayurvedic_audit": base_cognitive_rules + "\nAnalyze the primary Ayurvedic Dosha. Output JSON with 'asset' (vitality strengths), 'vulnerability' (energy drains without medical claims), and 'executive_pivot' (lifestyle rhythm adjustments).",
        "forecast": "Output a RAW JSON object with keys: 'structural_threats', 'strategic_windows', and 'executive_summary'. Use HTML bullets to break down the upcoming 24-month timeline transits."
    }

    eng_data = {}
    for chapter_key, system_prompt in swarm_chapters.items():
        send_message(chat_id, f"🧠 Synthesizing: {chapter_key.replace('_', ' ').title()}...")
        res = call_groq_agent(system_prompt, base_user_msg, MASTER_MODELS).strip()
        if res.startswith("```json"): res = res[7:]
        if res.startswith("```"): res = res[3:]
        if res.endswith("```"): res = res[:-3]
        try: eng_data[chapter_key] = json.loads(res.strip())
        except: eng_data[chapter_key] = {"asset": "Data Unavailable", "vulnerability": "Data Unavailable", "executive_pivot": "Data Unavailable"}
        time.sleep(15)

    cover_svg = generate_cover_page_svg(native_name="Confidential Profile", birth_str=session_data.get("birth_str", ""))
    rasi_svg = generate_rasi_chart_svg(session_data['planet_data'], session_data['asc_sign'])
    ephemeris_html = generate_ephemeris_table_html(session_data['planet_data'])
    
    timeline_data = calculate_vimshottari_timeline(session_data['planet_data']['Moon / Chandra']['lon'], session_data['dt_ist_iso'])
    dasha_html = generate_dasha_table_html(timeline_data)
    
    sav_heatmap_svg = generate_sav_heatmap_svg(session_data['sav'])
    mantra_html = generate_mantra_table_html(session_data['planet_data'], session_data['asc_sign'])
    lal_kitab_html = generate_remedies_table_html(session_data['remedies'])
    
    # We embed the sacred vectors directly into the HTML header
    sacred_header = f'<div class="fixed-header"><svg height="40" width="120" viewBox="0 0 160 40">{get_sacred_svg_symbols()}</svg></div>'

    def build_infographic_module(title, data_dict):
        if "structural_threats" in data_dict:
            return f"""
            <div class="infographic-module">
                <div class="info-content">
                    <h4 style="color:#B68A3A; text-transform:uppercase;">Strategic Windows</h4>
                    {data_dict.get('strategic_windows', '')}
                </div>
                <div class="info-content">
                    <h4 style="color:#A95D45; text-transform:uppercase;">Structural Threats</h4>
                    {data_dict.get('structural_threats', '')}
                </div>
                <div class="info-pivot">
                    <h4 style="color:#F5F0E6; text-transform:uppercase;">Executive Summary</h4>
                    {data_dict.get('executive_summary', '')}
                </div>
            </div>"""
        
        return f"""
        <div class="infographic-module">
            <div class="info-content">
                <h4 style="color:#71866B; text-transform:uppercase;">Strategic Asset</h4>
                {data_dict.get('asset', '')}
            </div>
            <div class="info-content">
                <h4 style="color:#A95D45; text-transform:uppercase;">Structural Vulnerability</h4>
                {data_dict.get('vulnerability', '')}
            </div>
            <div class="info-pivot">
                <h4 style="color:#F5F0E6; text-transform:uppercase;">Executive Pivot & Protocol Rationale</h4>
                {data_dict.get('executive_pivot', '')}
            </div>
        </div>
        """

    html_body = f"""
    <div class="cover-page">{cover_svg}</div>
    {sacred_header}
    
    <div class="content">
        <h2 class="section-title">01 — The Planetary Matrix</h2>
        <div class="grid-2col" style="align-items: center;">
            <div class="chart-box" style="margin-top: 10px;">{rasi_svg}</div>
            <div>{ephemeris_html}</div>
        </div>
        <div class="synopsis">
            <strong>Curator's Note:</strong> The D-1 chart (left) is the geometric snapshot of the heavens at your exact minute of birth. The numbers in the grid represent Zodiac Signs (1=Aries, 2=Taurus). The Ephemeris (right) reveals the mathematical operating system beneath it.
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">02 — Inner Operating System</h2>
        {build_infographic_module('Psychology', eng_data.get('psychology', {}))}

        <div class="page-break"></div>
        <h2 class="section-title">03 — Career & Wealth Canvas</h2>
        {build_infographic_module('Career & Wealth', eng_data.get('career_wealth', {}))}
        
        <h3 class="sub-title" style="margin-top: 30px;">Sarvashtakavarga (SAV) Karmic Heatmap</h3>
        <div class="sav-box">{sav_heatmap_svg}</div>
        <div class="synopsis" style="margin-top:10px;">
            <strong>Curator's Note:</strong> The SAV Heatmap reveals the mathematical strength of your 12 houses. Houses scoring above 28 points can easily absorb and manifest positive transit energies. Houses below 28 indicate areas requiring structural reinforcement.
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">04 — Relational Dynamics</h2>
        {build_infographic_module('Relational Karma', eng_data.get('relational_karma', {}))}

        <div class="page-break"></div>
        <h2 class="section-title">05 — Tactical Forecast</h2>
        <h3 class="sub-title">Vimshottari Timeline</h3>
        {dasha_html}
        <div class="synopsis">
            <strong>Curator's Note:</strong> The Vimshottari Dasha is a 120-year algorithmic timeline activated by the exact degree of your Moon. It acts as a karmic clock, indicating which specific planetary forces are currently awake.
        </div>
        <div style="margin-top:20px;">
            {build_infographic_module('Forecast', eng_data.get('forecast', {}))}
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">06 — Ayurvedic & Vitality Reflection</h2>
        <p style="font-size:9pt; color:#71866B; border:1px solid #B68A3A; padding:10px; background:#F5F0E6;">For personal reflection and traditional wellness context. It is not medical advice, diagnosis, or treatment.</p>
        <div style="margin-top:20px;">
            {build_infographic_module('Ayurvedic Audit', eng_data.get('ayurvedic_audit', {}))}
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">07 — Holistic Remediation Planner</h2>
        
        <h3 class="sub-title">I. Vedic Mantras & Spiritual Upayas</h3>
        <p style="font-size:9.5pt; margin-bottom:10px;">The following phonetic frequencies and traditional rituals target the Ascendant Lord and uniquely afflicted nodes within your geometry.</p>
        {mantra_html}
        
        <h3 class="sub-title" style="margin-top: 30px;">II. Lal Kitab Behavioral Protocols</h3>
        {lal_kitab_html}
        
        <div class="synopsis" style="margin-top:15px;">
            <strong>Curator's Note:</strong> While Mantras operate on phonetic resonance, Lal Kitab principles treat planets as energetic nodes that can be 'grounded' through physical, behavioral actions. The rationale for these specific actions is detailed in the 'Executive Pivot' sections of this report.
        </div>
    </div>
    """

    css = """
    @page { 
        size: letter; margin: 2.54cm; margin-top: 3.5cm;
        @bottom-right { content: counter(page); font-family: 'Helvetica', sans-serif; font-size: 9pt; color: #71866B; }
    }
    body { font-family: 'Helvetica', 'Arial', sans-serif; font-size: 10.5pt; line-height: 1.6; color: #101827; margin: 0; padding: 0; }
    .cover-page { height: 100vh; margin-top: -3.5cm; }
    .fixed-header { position: fixed; top: -2.5cm; left: 0; right: 0; text-align: center; }
    .page-break { page-break-before: always; }
    
    h1, h2.section-title { font-family: 'Georgia', serif; color: #101827; font-size: 18pt; text-transform: uppercase; letter-spacing: 2px; border-bottom: 1px solid #B68A3A; padding-bottom: 5px; margin-bottom: 25px; }
    h3.sub-title { font-family: 'Georgia', serif; color: #B68A3A; font-size: 14pt; text-transform: uppercase; letter-spacing: 1px; margin-top: 15px; margin-bottom: 10px; }
    
    .grid-2col { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 20px; }
    .grid-2col > div { width: 48%; box-sizing: border-box; }
    
    /* INFOGRAPHIC DIALECTIC GRID */
    .infographic-module { display: flex; flex-direction: column; gap: 15px; }
    .info-content { background: #F5F0E6; padding: 15px; border-left: 4px solid #101827; }
    .info-pivot { background: #101827; color: #F5F0E6; padding: 15px; border-left: 4px solid #B68A3A; }
    .info-content ul, .info-pivot ul { margin-top: 5px; padding-left: 20px; }
    .info-content li, .info-pivot li { margin-bottom: 8px; }
    
    .synopsis { font-size: 9.5pt; color: #58708C; background: #F5F0E6; padding: 12px; border-left: 4px solid #B68A3A; margin-top: 15px; margin-bottom: 20px; font-style: italic; line-height: 1.5; }
    
    table.data-table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 9pt; }
    table.data-table th { background-color: #101827; color: #B68A3A; padding: 10px; text-align: left; text-transform: uppercase; letter-spacing: 1px; }
    table.data-table td { padding: 10px; border-bottom: 1px solid #e0e0e0; vertical-align: middle; }
    table.data-table tr:nth-child(even) { background-color: #F5F0E6; }
    
    .chart-box { text-align: center; margin-bottom: 20px; }
    .sav-box { text-align: center; }
    """
    full_html = f"<html><head><style>{css}</style></head><body>{html_body}</body></html>"
    
    pdf_path = f"/tmp/Celestial_Strategy_{int(time.time())}.pdf"
    if generate_pdf_weasyprint(full_html, pdf_path): send_document(chat_id, pdf_path)

# ==========================================
# FLASK WEBHOOK
# ==========================================
@app.route('/', methods=['POST', 'GET'])
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "Active Premium Overhauled Server", 200
    try:
        update = request.get_json(silent=True)
        if not update or "message" not in update or "text" not in update["message"]: return jsonify(status="ignored"), 200
            
        chat_id = update["message"]["chat"]["id"]
        user_text = update["message"]["text"].strip()
            
        if user_text.startswith("/start"):
            clear_session(chat_id)
            send_message(chat_id, "Welcome to the Celestial Strategy Bot. Send birth details: `DD-MM-YYYY HH:MM City`")
            return jsonify(status="success"), 200
                
        match = re.search(r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{2,4})\s+(\d{1,2}):(\d{1,2})\s+(.+)', user_text)
        if match:
            day, month, year, hour, minute, city_input = match.groups()
            day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
            year = year + (1900 if year > 25 else 2000) if year < 100 else year
            send_message(chat_id, "⏳ Calculating geometric and astronomical arrays...")
            try:
                res = requests.get(f"[https://nominatim.openstreetmap.org/search?q=](https://nominatim.openstreetmap.org/search?q=){city_input}&format=json&limit=1", headers={'User-Agent': 'Bot/1.0'}, timeout=5).json()
                lat, lon = float(res[0]['lat']), float(res[0]['lon'])
                city_clean = res[0].get('display_name', city_input).split(',')[0]
            except: 
                lat, lon = 30.7333, 76.7794
                city_clean = city_input
                    
            asc_sign, planets, houses, sav, logic_breakdown, dt_ist = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
            remedies = get_applicable_remedies(houses, planets)
            session = {
                "state": "ready", "asc_sign": asc_sign, "planet_data": planets, "houses": houses, "sav": sav, "dt_ist_iso": dt_ist,
                "remedies": remedies, "logic_breakdown": logic_breakdown,
                "birth_str": f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean}"
            }
            save_session(chat_id, session)
            threading.Thread(target=process_background_task, args=(chat_id, session)).start()
            return jsonify(status="success"), 200
            
    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        
    return jsonify(status="success"), 200

# INITIALIZE DB OUTSIDE BLOCK FOR GUNICORN (RENDER)
init_db()

if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
