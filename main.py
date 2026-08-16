import os
import requests
import re
import time
import sqlite3
import threading
import json
import markdown2
from weasyprint import HTML
from datetime import datetime, timedelta
import swisseph as swe
from flask import Flask, request, jsonify

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
DB_PATH = os.environ.get("DB_PATH", "/tmp/bot.db")

# ==========================================
# CORE CONSTANTS & MATH TABLES
# ==========================================
ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
HINDI_SIGNS = {"Aries": "Aries (Mesha)", "Taurus": "Taurus (Vrishabha)", "Gemini": "Gemini (Mithuna)", "Cancer": "Cancer (Karka)", "Leo": "Leo (Simha)", "Virgo": "Virgo (Kanya)", "Libra": "Libra (Tula)", "Scorpio": "Scorpio (Vrishchika)", "Sagittarius": "Sagittarius (Dhanu)", "Capricorn": "Capricorn (Makara)", "Aquarius": "Aquarius (Kumbha)", "Pisces": "Pisces (Meena)"}
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
DASHA_LORDS = [("Ketu", 7), ("Venus (Shukra)", 20), ("Sun (Surya)", 6), ("Moon (Chandra)", 10), ("Mars (Mangal)", 7), ("Rahu", 18), ("Jupiter (Guru)", 16), ("Saturn (Shani)", 19), ("Mercury (Budh)", 17)]
EXALTATION = {"Sun (Surya)": "Aries", "Moon (Chandra)": "Taurus", "Mars (Mangal)": "Capricorn", "Mercury (Budh)": "Virgo", "Jupiter (Guru)": "Cancer", "Venus (Shukra)": "Pisces", "Saturn (Shani)": "Libra", "Rahu": "Taurus", "Ketu": "Scorpio"}
DEBILITATION = {"Sun (Surya)": "Libra", "Moon (Chandra)": "Scorpio", "Mars (Mangal)": "Cancer", "Mercury (Budh)": "Pisces", "Jupiter (Guru)": "Capricorn", "Venus (Shukra)": "Virgo", "Saturn (Shani)": "Aries", "Rahu": "Scorpio", "Ketu": "Taurus"}
OWN_SIGNS = {"Sun (Surya)": ["Leo"], "Moon (Chandra)": ["Cancer"], "Mars (Mangal)": ["Aries", "Scorpio"], "Mercury (Budh)": ["Gemini", "Virgo"], "Jupiter (Guru)": ["Sagittarius", "Pisces"], "Venus (Shukra)": ["Taurus", "Libra"], "Saturn (Shani)": ["Capricorn", "Aquarius"]}
COMBUSTION_ORB = {"Moon (Chandra)": 12, "Mars (Mangal)": 17, "Mercury (Budh)": 14, "Jupiter (Guru)": 11, "Venus (Shukra)": 10, "Saturn (Shani)": 15}
MALEFICS = ["Saturn (Shani)", "Mars (Mangal)", "Rahu", "Ketu", "Sun (Surya)"]
NAK_LORDS = ["Ketu", "Venus (Shukra)", "Sun (Surya)", "Moon (Chandra)", "Mars (Mangal)", "Rahu", "Jupiter (Guru)", "Saturn (Shani)", "Mercury (Budh)"]

# Bhinnashtakavarga (BAV) Kakshya Tables
BAV_TABLES = {
    "Sun (Surya)": [0,0,1,1,0,0,1,1, 1,0,0,0,1,1,0,0, 0,1,1,0,0,1,1,0, 0,0,1,1,0,0,1,1, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 0,0,0,1,1,1,1,0, 1,1,1,0,0,0,0,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0],
    "Moon (Chandra)": [0,1,0,1,1,0,1,0, 1,0,1,0,0,1,0,1, 1,1,0,0,1,1,0,0, 0,1,1,0,1,0,1,0, 1,0,1,1,0,1,0,1, 0,1,0,1,1,0,1,0, 1,1,0,1,0,1,1,0, 0,0,1,1,1,1,0,0, 1,1,0,0,0,0,1,1, 0,0,1,1,1,1,0,0, 1,0,1,0,0,1,0,1, 0,1,0,1,1,0,1,0],
    "Mars (Mangal)": [1,0,0,1,1,0,0,1, 1,1,0,0,1,1,0,0, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 0,1,1,0,1,0,1,0, 1,0,1,0,0,1,0,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,0,1,1,1,1,0],
    "Mercury (Budh)": [0,1,1,0,1,0,0,1, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,1,0,0,1,1,0,0],
    "Jupiter (Guru)": [0,1,1,1,0,0,0,0, 1,0,0,0,1,1,1,0, 1,1,0,0,0,0,1,1, 0,0,1,1,1,1,0,0, 1,1,1,0,0,0,0,1, 0,0,0,1,1,1,1,0, 0,1,1,0,1,0,1,0, 1,0,0,1,0,1,0,1, 0,1,1,1,0,0,0,0, 1,0,0,0,1,1,1,0, 0,0,0,1,1,1,1,0, 1,1,1,0,0,0,0,1],
    "Venus (Shukra)": [1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 0,1,1,0,1,0,1,0, 1,0,0,1,0,1,0,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0],
    "Saturn (Shani)": [0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,0,0,1,1,0, 0,1,0,1,1,0,0,1, 1,0,1,0,1,0,0,1, 0,1,0,1,0,1,1,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0]
}

# ==========================================
# DATABASE MANAGER (SQLite Stateless Architecture)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (chat_id INTEGER PRIMARY KEY, session_data TEXT)''')
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
# ASTROLOGY MATH ENGINE
# ==========================================
def get_nakshatra_info(lon):
    nak_span = 360.0 / 27.0
    nak_idx = int(lon / nak_span) % 27
    rem = lon % nak_span
    pada = int(rem / (nak_span / 4.0)) + 1
    return nak_idx, NAKSHATRAS[nak_idx], pada, rem

def get_planet_dignity(planet, sign):
    if EXALTATION.get(planet) == sign: return "Exalted (Uchcha)"
    if DEBILITATION.get(planet) == sign: return "Debilitated (Neecha)"
    if planet in OWN_SIGNS and sign in OWN_SIGNS[planet]: return "Own Sign (Swavritti)"
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

def calculate_bav(planet_name, target_house, houses_dict):
    if planet_name not in BAV_TABLES: return 0
    table = BAV_TABLES[planet_name]
    p_house = get_house_of_planet(houses_dict, planet_name)
    if not p_house: return 0
    rel_house = ((target_house - p_house) % 12) + 1
    start_idx = (rel_house - 1) * 8
    return sum(table[start_idx : start_idx + 8])

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
            a_idx = current_lord_idx
            a_years = (DASHA_LORDS[a_idx][1] * DASHA_LORDS[current_lord_idx][1]) / 120.0
            y_passed_ad = years_passed_after_balance
            
            while y_passed_ad > a_years:
                y_passed_ad -= a_years
                a_idx = (a_idx + 1) % 9
                a_years = (DASHA_LORDS[a_idx][1] * DASHA_LORDS[current_lord_idx][1]) / 120.0
                
            prev_a_idx = (a_idx - 1) % 9
            next_a_idx = (a_idx + 1) % 9
            return f"Past: {lord}-{DASHA_LORDS[prev_a_idx][0]} | Current: {lord}-{DASHA_LORDS[a_idx][0]} | Future: {lord}-{DASHA_LORDS[next_a_idx][0]}"
            
        years_passed_after_balance -= span
        current_lord_idx = (current_lord_idx + 1) % 9
        
    return f"{DASHA_LORDS[current_lord_idx][0]} Mahadasha"

def calculate_charadasha(asc_sign, planets_full, birth_dt):
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    sign_lords = {"Aries": "Mars (Mangal)", "Taurus": "Venus (Shukra)", "Gemini": "Mercury (Budh)", "Cancer": "Moon (Chandra)", "Leo": "Sun (Surya)", "Virgo": "Mercury (Budh)", "Libra": "Venus (Shukra)", "Scorpio": "Mars (Mangal)", "Sagittarius": "Jupiter (Guru)", "Capricorn": "Saturn (Shani)", "Aquarius": "Saturn (Shani)", "Pisces": "Jupiter (Guru)"}
    
    if asc_idx in [0, 3, 6, 9]: start_idx = asc_idx 
    elif asc_idx in [1, 4, 7, 10]: start_idx = (asc_idx + 8) % 12 
    else: start_idx = (asc_idx + 4) % 12 
    
    ninth_idx = (asc_idx + 8) % 12
    direction = 1 if (ninth_idx % 2 == 0) else -1 
    
    dashas = []
    curr_idx = start_idx
    for _ in range(12):
        sign_name = ZODIAC_SIGNS[curr_idx]
        lord = sign_lords.get(sign_name)
        lord_sign = planets_full.get(lord, {}).get("sign")
        lord_idx = ZODIAC_SIGNS.index(lord_sign) if lord_sign else curr_idx
        
        if curr_idx == lord_idx:
            duration = 12
        else:
            duration = abs((lord_idx - curr_idx) * direction) % 12
            if duration == 0: duration = 12
            
        dashas.append({"sign": sign_name, "lord": lord, "duration": duration})
        curr_idx = (curr_idx + direction) % 12
        
    return f"Current Charadasha Sequence: {dashas[0]['sign']} ({dashas[0]['duration']}y) -> {dashas[1]['sign']} ({dashas[1]['duration']}y) -> {dashas[2]['sign']} ({dashas[2]['duration']}y)"

def calculate_multi_transits_with_bav(natal_moon_sign, natal_asc_sign, houses_dict):
    now_dt = datetime.now()
    swe.set_ephe_path(None); swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    dt_utc = now_dt - timedelta(hours=5, minutes=30)
    utc_decimal = dt_utc.hour + (dt_utc.minute / 60.0)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal)
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    
    t_sat = swe.calc_ut(jdut, swe.SATURN, flags); sat_lon = t_sat[0][0] if isinstance(t_sat[0], tuple) else t_sat[0]
    t_jup = swe.calc_ut(jdut, swe.JUPITER, flags); jup_lon = t_jup[0][0] if isinstance(t_jup[0], tuple) else t_jup[0]
    
    transit_sat_sign = ZODIAC_SIGNS[int(sat_lon / 30) % 12]
    transit_jup_sign = ZODIAC_SIGNS[int(jup_lon / 30) % 12]
    
    moon_idx = ZODIAC_SIGNS.index(natal_moon_sign)
    asc_idx = ZODIAC_SIGNS.index(natal_asc_sign)
    
    sat_house_from_moon = ((ZODIAC_SIGNS.index(transit_sat_sign) - moon_idx) % 12) + 1
    sat_house_from_asc = ((ZODIAC_SIGNS.index(transit_sat_sign) - asc_idx) % 12) + 1
    
    jup_house_from_moon = ((ZODIAC_SIGNS.index(transit_jup_sign) - moon_idx) % 12) + 1
    jup_house_from_asc = ((ZODIAC_SIGNS.index(transit_jup_sign) - asc_idx) % 12) + 1
    
    sat_bav_moon = calculate_bav("Saturn (Shani)", sat_house_from_moon, houses_dict)
    sat_bav_asc = calculate_bav("Saturn (Shani)", sat_house_from_asc, houses_dict)
    jup_bav_moon = calculate_bav("Jupiter (Guru)", jup_house_from_moon, houses_dict)
    jup_bav_asc = calculate_bav("Jupiter (Guru)", jup_house_from_asc, houses_dict)
    
    return f"Saturn Transiting House {sat_house_from_moon} from Moon (BAV: {sat_bav_moon}/8) & House {sat_house_from_asc} from Lagna (BAV: {sat_bav_asc}/8). Jupiter Transiting House {jup_house_from_moon} from Moon (BAV: {jup_bav_moon}/8) & House {jup_house_from_asc} from Lagna (BAV: {jup_bav_asc}/8)."

def calculate_chart_logic(asc_sign, planets_full, birth_dt, sun_lon):
    now = datetime.now()
    age = (now - birth_dt).days // 365
    if age < 18: life_stage = f"CHILD (Age {age}): STRICTLY focus on House 4, 5, 9."
    elif 18 <= age <= 25: life_stage = f"YOUNG ADULT (Age {age}): Focus on House 9, 10, 1."
    elif 26 <= age <= 40: life_stage = f"ESTABLISHMENT (Age {age}): Deep dive into House 10, 7, 2, 6."
    elif 41 <= age <= 60: life_stage = f"CONSOLIDATION (Age {age}): Focus on House 11, 2, 8, 10."
    else: life_stage = f"ELDER (Age {age}): STRICTLY focus on House 9, 12, 8, 4."

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
    
    logic_summary = f"[LIFE STAGE FILTER]: {life_stage}\n{fact_sheet}"
    
    vimshottari = calculate_vimshottari_dasha(planets_full["Moon (Chandra)"]["lon"], birth_dt, now)
    charadasha = calculate_charadasha(asc_sign, planets_full, birth_dt)
    logic_summary += f"\n[VIMSHOTTARI DASHA]: {vimshottari}"
    logic_summary += f"\n[JAIMINI CHARADASHA]: {charadasha}"
    
    transit_data = calculate_multi_transits_with_bav(planets_full["Moon (Chandra)"]["sign"], asc_sign, houses)
    logic_summary += f"\n[BAV TRANSIT MATRIX]: {transit_data}"

    return logic_summary, age

def calculate_sidereal_chart(day, month, year, hour, minute, lat, lon):
    swe.set_ephe_path(None); swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    dt_ist = datetime(year, month, day, hour, minute)
    dt_utc = dt_ist - timedelta(hours=5, minutes=30)
    utc_decimal = dt_utc.hour + (dt_utc.minute / 60.0)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal)
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    planets = {"Sun (Surya)": swe.SUN, "Moon (Chandra)": swe.MOON, "Mars (Mangal)": swe.MARS, "Mercury (Budh)": swe.MERCURY, "Jupiter (Guru)": swe.JUPITER, "Venus (Shukra)": swe.VENUS, "Saturn (Shani)": swe.SATURN, "Rahu": swe.MEAN_NODE, "Ketu": 10}
    positions = {}; rahu_lon = 0.0; moon_lon = 0.0; sun_lon = 0.0
    
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
        nak_lord = NAK_LORDS[nak_idx % 9] 
        
        dignity = get_planet_dignity(name, sign_name)
        is_retro = speed < 0 if name not in ["Sun (Surya)", "Moon (Chandra)"] else False
        is_combust = False
        if name in COMBUSTION_ORB:
            dist_to_sun = abs(lon_val - sun_lon)
            if dist_to_sun > 180: dist_to_sun = 360 - dist_to_sun
            if dist_to_sun < COMBUSTION_ORB[name]: is_combust = True
                
        positions[name] = {
            "sign": sign_name, "hindi_sign": HINDI_SIGNS[sign_name], "lon": lon_val % 360.0, 
            "nak": nak_name, "nak_lord": nak_lord, "pada": pada, 
            "dignity": dignity, "retro": is_retro, "combust": is_combust
        }
        
    try: 
        _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags); asc_lon = ascmc[0] % 360.0
    except: 
        asc_lon = 0.0
        
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]; _, asc_nak, asc_pada, _ = get_nakshatra_info(asc_lon)
    logic_breakdown, age = calculate_chart_logic(asc_sign, positions, dt_ist, sun_lon)
    
    return asc_sign, asc_nak, asc_pada, positions, logic_breakdown, age

# ==========================================
# LLM ORCHESTRATION & PDF PIPELINE
# ==========================================
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def send_document(chat_id, file_path):
    url = f"{TELEGRAM_API_URL}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            requests.post(url, data={'chat_id': chat_id}, files={'document': f}, timeout=30)
    except: pass

def call_groq_agent(groq_key, groq_url, model_name, system_msg, user_msg):
    payload = {"model": model_name, "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}], "temperature": 0.3}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
    try:
        res = requests.post(groq_url, headers=headers, json=payload, timeout=180)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        return "[ERROR IN AGENT]"
    except:
        return "[AGENT TIMEOUT]"

def llm_output_firewall(text, logic_summary):
    """Post-generation validation that strips hallucinated aspects and cleans fluff."""
    none_houses = re.findall(r"House (\d+).*?Aspected by: none\.", logic_summary, re.IGNORECASE)
    clean_text = text
    for h_num in none_houses:
        pattern = rf'(?i)([^.]*aspect[^.]*House {h_num}[^.]*\.)|([^.]House {h_num}[^.]*aspect[^.]*\.)'
        def replace_func(match):
            if "no planetary" in match.group(0).lower() or "none" in match.group(0).lower():
                return match.group(0)
            return " [REDACTED: HALLUCINATED ASPECT] "
        clean_text = re.sub(pattern, replace_func, clean_text)
        
    replacements = {
        r"\bpotentially\b": "",
        r"\bpossibly\b": "",
        r"\bsuggesting that\b": "indicating that",
        r"\bsuggests that\b": "indicates that",
        r"\bsuggests a need\b": "mandates a need",
        r"\bassuming\b": "",
        r"\bself-care\b": "tactical remediation",
        r"\bdate nights\b": "structured relational protocols",
        r"\byoga\b": "Ayurvedic physical routines",
        r"\bmeditation\b": "targeted mantric resonance",
        r"\bmindfulness\b": "clinical situational awareness"
    }
    
    for pattern, replacement in replacements.items():
        clean_text = re.compile(pattern, re.IGNORECASE).sub(replacement, clean_text)
        
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def generate_pdf_weasyprint(report_text, pdf_path):
    try:
        html_body = markdown2.markdown(report_text, extras=["tables", "fenced-code-blocks"])
        css = """
        @page { size: letter; margin: 2cm; }
        body { font-family: 'Noto Sans', 'Noto Sans Devanagari', sans-serif; font-size: 11pt; line-height: 1.5; color: #222; }
        h1 { color: #4A154B; font-size: 16pt; border-bottom: 2px solid #4A154B; padding-bottom: 5px; margin-top: 20px; }
        h2 { color: #1D1C1D; font-size: 13pt; margin-top: 15px; }
        h3 { color: #555; font-size: 11pt; font-style: italic; }
        strong { color: #111; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th { background-color: #4A154B; color: white; padding: 8px; text-align: left; font-size: 9pt; }
        td { border: 1px solid #ddd; padding: 8px; font-size: 9pt; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        ul, ol { padding-left: 20px; }
        li { margin-bottom: 5px; }
        """
        full_html = f"<html><head><style>{css}</style></head><body>{html_body}</body></html>"
        HTML(string=full_html).write_pdf(pdf_path)
        return True
    except Exception as e:
        print(f"WEASYPRINT ERROR: {e}", flush=True)
        return False

def process_background_task(chat_id, session_data):
    """The heavy asynchronous task that generates the report."""
    groq_key = os.environ.get("GROQ_API_KEY")
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    
    send_message(chat_id, "⏳ Initiating Deep Correlation Audit Pipeline...")
    
    system_msg = """You are an Elite Forensic Astrological Diagnostician writing an institutional Threat Matrix Dossier. 
[ABSOLUTE LAWS - VIOLATION = FAILURE]
1. NARRATIVE FLOW: Psychological Baseline -> Past -> Present Trigger -> Future Survival.
2. NO REPETITION: State the "Astronomical Root" ONCE. Use "As established by..." to correlate.
3. DEEP CORRELATION: Link the 5-Pillar Ecosystem data to real-world manifestations.
4. BAV INTEGRATION: You MUST explicitly cite the BAV scores (0-8) when analyzing transits. A BAV of 0-2 is severe friction; 6-8 is high relief.
5. FORBIDDEN CONCEPTS: Do not use 'potentially', 'possibly', 'suggesting', 'assuming', 'yoga', 'meditation'. Use definitive clinical terms.
6. LAL KITAB STRICTNESS: You MUST copy-paste the exact remedies provided in the [MANDATORY LAL KITAB REMEDY] section verbatim. Do NOT invent generic remedies like 'perform puja' or 'practice yoga'. If the logic summary says 'Drop raw coal', you write 'Drop raw coal'.
7. HINDI MANDATORY: Use Hindi names for EVERY Zodiac Sign and Planet.
"""
    logic = session_data['logic_breakdown']
    planet_summary = session_data['planet_summary']
    
    user_msg_eng = f"""[INPUT DATA]
- Baseline Date: {datetime.now().strftime("%B %d, %Y")}
{logic}
[PLANETARY ARRAY]
Ascendant (Lagna): {session_data['asc_sign']}
{planet_summary}

[OUTPUT TEMPLATE - FOLLOW EXACTLY]
*Disclaimer: This audit maps karmic tendencies and probabilistic risk vectors based on planetary mathematics.*

# I. THE TEMPORAL-PSYCHOLOGICAL NARRATIVE
- **The Psychological Baseline:** Diagnose the native's core psychological bottleneck based on the Atmakaraka and Moon's Nakshatra.
- **The Historical Trajectory:** Analyze the Past Vimshottari Antardasha.
- **The Present Trigger:** Pinpoint the exact trigger using Current Vimshottari/Charadasha and the BAV Transit Matrix. Explicitly state the BAV scores.
- **The Expected State & Survival:** Map the survival trajectory based on the Future Antardasha.

# II. THE 3-PILLAR THREAT MATRIX
*(Analyze using: Astronomical Root -> Systemic Vulnerability -> Real-World Manifestation -> Tactical Countermeasure)*

**Pillar 1: Wealth, Career & Structural Stability**
- Analyze Houses 2, 10, 11.
- Provide Financial triage and Gemstone prescriptions.

**Pillar 2: Relationship, Property & Progeny Dynamics**
- Analyze Houses 4, 5, 7, 9.
- Provide Environmental/Vastu corrections.

**Pillar 3: Core Vitality & Subconscious Trajectory (D9)**
- Analyze Houses 1, 3.
- Provide Physical routines and D9 remedies.

# III. AYURVEDIC & NEUROLOGICAL AUDIT
- **Dosha Analysis:** Diagnose the exact physical imbalance (Vata/Pitta/Kapha).
- **Ayurvedic Triage Protocol:** Prescribe specific dietary shifts and lifestyle modifications.

# IV. WHOLISTIC LAL KITAB REMEDIATION
- **Immediate First Aid:** The most urgent karmic actions.
- **Holistic Protocol:** Compile remaining remedies into a weekly schedule.
- **Long-Term Mantras:** Specific mantras for the Lagna Lord.
"""
    
    english_text = call_groq_agent(groq_key, groq_url, "llama-3.3-70b-versatile", system_msg, user_msg_eng)
    if "[ERROR" in english_text or "[AGENT" in english_text:
        send_message(chat_id, "⚠️ Master Agent failed.")
        return

    # Apply the Smart Firewall to clean fluff and bad grammar
    english_text = llm_output_firewall(english_text, logic)

    # Hindi Translation (Using 70B to prevent cutoff)
    translator_system_msg = """You are an expert astrological translator. Translate the provided English astrological dossier into formal, clinical Hindi. 
    Maintain all Markdown formatting. 
    Ensure English astrological terms have their Hindi names in brackets (e.g., Saturn (Shani)). 
    DO NOT put Hindi words in brackets if they are already in Devanagari script. 
    Do not add or remove information. Translate exactly."""
    
    hindi_text = call_groq_agent(groq_key, groq_url, "llama-3.3-70b-versatile", translator_system_msg, f"Translate the following text to Hindi:\n\n{english_text}")
    
    complete_pdf_text = english_text + "\n\n# PART 2: हिंदी अनुवाद (HINDI TRANSLATION)\n\n" + hindi_text
    
    send_message(chat_id, "⏳ Compiling Forensic Dossier PDF...")
    file_tag = str(int(time.time()))
    pdf_path = f"/tmp/Astrological_Audit_{file_tag}.pdf"
    
    if generate_pdf_weasyprint(complete_pdf_text, pdf_path) and os.path.exists(pdf_path):
        send_document(chat_id, pdf_path)
        send_message(chat_id, "📄 **Astrological Audit PDF attached above!** ⬆️")
    else:
        send_message(chat_id, "⚠️ PDF generation failed. Sending text report:")
        for i in range(0, len(complete_pdf_text), 3900): send_message(chat_id, complete_pdf_text[i:i + 3900]); time.sleep(0.5)

# ==========================================
# FLASK WEBHOOK (Instant Return + Threading)
# ==========================================
@app.route('/', methods=['POST', 'GET'])
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': return "Render Persistent Bot Server is Active", 200
    
    try:
        update = request.get_json(silent=True)
        if not update: return jsonify(status="ignored"), 200
            
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"].strip()
            
            if user_text.startswith("/start"):
                clear_session(chat_id)
                send_message(chat_id, "Welcome! Send your birth details to begin your **Astrological Audit**:\n`DD-MM-YYYY HH:MM City`\n(e.g., `05-09-1981 12:16 Amritsar`)")
                return jsonify(status="success"), 200
                
            match = re.search(r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{2,4})\s+(\d{1,2}):(\d{1,2})\s+(.+)', user_text)
            session = get_session(chat_id)
            
            # STATE 1: Awaiting Partner details
            if match and session and session.get("state") == "awaiting_partner":
                day, month, year, hour, minute, city_input = match.groups()
                day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                if year < 100: year += 1900 if year > 25 else 2000
                
                send_message(chat_id, "⏳ Partner chart calculating in background...")
                
                url = f"https://nominatim.openstreetmap.org/search?q={city_input}&format=json&limit=1"
                try:
                    res = requests.get(url, headers={'User-Agent': 'PanditjiBot/1.0'}, timeout=5).json()
                    lat, lon = float(res[0]['lat']), float(res[0]['lon'])
                except:
                    lat, lon = 30.7333, 76.7794
                
                p2_asc, p2_nak, p2_pada, p2_planets, p2_logic, p2_age = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                
                p1_moon_idx, _, _, _ = get_nakshatra_info(session['planet_data']["Moon (Chandra)"]["lon"])
                p2_moon_idx, _, _, _ = get_nakshatra_info(p2_planets["Moon (Chandra)"]["lon"])
                nadi_dosha = (p1_moon_idx % 3) == (p2_moon_idx % 3)
                
                session["synastry"] = f"Partner Compatibility: {'NADI DOSHA DETECTED (High risk).' if nadi_dosha else 'No Nadi Dosha.'}"
                session["state"] = "ready_to_generate"
                save_session(chat_id, session)
                
                threading.Thread(target=process_background_task, args=(chat_id, session)).start()
                return jsonify(status="success"), 200

            # STATE 2: Initial Birth Details
            elif match:
                send_message(chat_id, "✅ Chart calculated. \n\nDo you want to analyze compatibility with a partner? \nSend their details (DD-MM-YYYY HH:MM City) or type 'skip'.")
                
                day, month, year, hour, minute, city_input = match.groups()
                day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                if year < 100: year += 1900 if year > 25 else 2000
                
                url = f"https://nominatim.openstreetmap.org/search?q={city_input}&format=json&limit=1"
                try:
                    res = requests.get(url, headers={'User-Agent': 'PanditjiBot/1.0'}, timeout=5).json()
                    lat, lon = float(res[0]['lat']), float(res[0]['lon'])
                    city_clean = res[0].get('display_name', city_input).split(',')[0]
                except:
                    lat, lon = 30.7333, 76.7794
                    city_clean = city_input
                    
                asc_sign, asc_nak, asc_pada, planets, logic_breakdown, age = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                planet_summary = "\n".join([f"- {p}: {d['hindi_sign']} | Nak: {d['nak']} (ruled by {d.get('nak_lord', 'Unknown')}) | Dignity: {d['dignity']}" for p, d in planets.items()])
                
                session = {
                    "state": "awaiting_partner",
                    "asc_sign": asc_sign, "planet_summary": planet_summary,
                    "planet_data": planets, "logic_breakdown": logic_breakdown, "age": age,
                    "birth_str": f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean} (Age: {age})"
                }
                save_session(chat_id, session)
                return jsonify(status="success"), 200

            # STATE 3: Skip Partner
            elif session and session.get("state") == "awaiting_partner" and user_text.lower() == 'skip':
                session["state"] = "ready_to_generate"
                save_session(chat_id, session)
                threading.Thread(target=process_background_task, args=(chat_id, session)).start()
                return jsonify(status="success"), 200
                
            # STATE 4: Follow-up Questions (Sync, but fast)
            elif session and session.get("state") == "ready_to_generate":
                send_message(chat_id, "Running follow-up analysis...")
                groq_key = os.environ.get("GROQ_API_KEY")
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                q_prompt = f"You are an elite Vedic Astrologer. Answer directly based on this data:\n{session['logic_breakdown']}\nQuestion: {user_text}"
                payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": q_prompt}], "temperature": 0.3}
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
                res = requests.post(groq_url, headers=headers, json=payload, timeout=90)
                if res.status_code == 200:
                    answer = res.json()['choices'][0]['message']['content']
                    for i in range(0, len(answer), 3900): send_message(chat_id, answer[i:i + 3900]); time.sleep(0.5)
                else: send_message(chat_id, "Error processing your question.")
                return jsonify(status="success"), 200
            else:
                send_message(chat_id, "Please send birth details: `DD-MM-YYYY HH:MM City`")
                return jsonify(status="success"), 200

    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        
    return jsonify(status="success"), 200

# Initialize database on module load (required for Gunicorn on Render)
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
