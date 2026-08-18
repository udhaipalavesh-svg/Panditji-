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
DOSHA_MAP = {"Aries": "Pitta", "Taurus": "Kapha", "Gemini": "Vata", "Cancer": "Kapha", "Leo": "Pitta", "Virgo": "Vata", "Libra": "Vata", "Scorpio": "Kapha", "Sagittarius": "Pitta", "Capricorn": "Vata", "Aquarius": "Vata", "Pisces": "Kapha"}

BAV_TABLES = {
    "Sun (Surya)": [0,0,1,1,0,0,1,1, 1,0,0,0,1,1,0,0, 0,1,1,0,0,1,1,0, 0,0,1,1,0,0,1,1, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 0,0,0,1,1,1,1,0, 1,1,1,0,0,0,0,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0],
    "Moon (Chandra)": [0,1,0,1,1,0,1,0, 1,0,1,0,0,1,0,1, 1,1,0,0,1,1,0,0, 0,1,1,0,1,0,1,0, 1,0,1,1,0,1,0,1, 0,1,0,1,1,0,1,0, 1,1,0,1,0,1,1,0, 0,0,1,1,1,1,0,0, 1,1,0,0,0,0,1,1, 0,0,1,1,1,1,0,0, 1,0,1,0,0,1,0,1, 0,1,0,1,1,0,1,0],
    "Mars (Mangal)": [1,0,0,1,1,0,0,1, 1,1,0,0,1,1,0,0, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 0,1,1,0,1,0,1,0, 1,0,1,0,0,1,0,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,0,1,1,1,1,0],
    "Mercury (Budh)": [0,1,1,0,1,0,0,1, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,1,0,0,1,1,0,0],
    "Jupiter (Guru)": [0,1,1,1,0,0,0,0, 1,0,0,0,1,1,1,0, 1,1,0,0,0,0,1,1, 0,0,1,1,1,1,0,0, 1,1,1,0,0,0,0,1, 0,0,0,1,1,1,1,0, 0,1,1,0,1,0,1,0, 1,0,0,1,0,1,0,1, 0,1,1,1,0,0,0,0, 1,0,0,0,1,1,1,0, 0,0,0,1,1,1,1,0, 1,1,1,0,0,0,0,1],
    "Venus (Shukra)": [1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 0,1,1,0,1,0,1,0, 1,0,0,1,0,1,0,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0],
    "Saturn (Shani)": [0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,0,0,1,1,0, 0,1,0,1,1,0,0,1, 1,0,1,0,1,0,0,1, 0,1,0,1,0,1,1,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0]
}

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
    "Saturn (Shani)_1": "Do not consume non-veg on Saturday. Feed black crows daily to prevent chronic fatigue and identity erosion.",
    "Mars (Mangal)_1": "Donate red lentils on Tuesday. Avoid keeping weapons in the house to prevent aggressive outbursts.",
    "Rahu_1": "Keep a silver square in pocket. Do not accept electrical items as gifts to prevent identity confusion.",
    "Ketu_1": "Feed street dogs daily. Do not wear fragmented jewelry to prevent scattered focus.",
    "Sun (Surya)_1": "Offer water to the Sun daily. Do not consume salt on Sundays to maintain vitality.",
    "Saturn (Shani)_2": "Keep a silver square in wallet. Serve food to disabled people to prevent wealth erosion.",
    "Mars (Mangal)_2": "Donate red masoor dal on Tuesday. Do not keep iron tools in the kitchen to prevent family disputes.",
    "Rahu_2": "Keep a solid silver ball in the mouth for a few minutes daily. Do not accept bribes to prevent wealth loss.",
    "Ketu_2": "Donate a black and white blanket. Do not keep broken glass in the house to prevent wealth leakage.",
    "Sun (Surya)_2": "Donate wheat and jaggery on Sunday. Do not consume hot food to prevent family arguments.",
    "Saturn (Shani)_4": "Do not build a house before age 48. Pour mustard oil on the floor on Saturday to prevent domestic disputes.",
    "Mars (Mangal)_4": "Keep a square piece of red copper in the house. Do not keep weapons under the bed to prevent domestic violence.",
    "Rahu_4": "Keep a solid silver square in the house. Do not keep electronic items in the bedroom to prevent insomnia.",
    "Ketu_4": "Feed street dogs daily. Do not keep fragmented items in the house to prevent domestic unrest.",
    "Sun (Surya)_4": "Offer water to the Sun daily. Do not consume salt on Sundays to maintain domestic peace.",
    "Saturn (Shani)_5": "Do not build a house before age 48. Feed black crows to prevent delays in progeny.",
    "Mars (Mangal)_5": "Donate red lentils on Tuesday. Do not keep weapons in the bedroom to prevent miscarriages.",
    "Rahu_5": "Keep a silver square in pocket. Do not accept electrical items as gifts to prevent progeny issues.",
    "Ketu_5": "Feed street dogs daily. Do not wear fragmented jewelry to prevent progeny delays.",
    "Sun (Surya)_5": "Offer water to the Sun daily. Do not consume salt on Sundays to maintain progeny health.",
    "Saturn (Shani)_6": "Float a black mustard oil-filled bottle in a river on Saturday. Serve food to disabled people to ward off chronic debts and prolonged illnesses.",
    "Mars (Mangal)_6": "Donate red masoor dal and batasha (sweet) on Tuesday. Feed a monkey or a red dog to neutralize enemies and prevent aggressive litigation.",
    "Rahu_6": "Float a piece of lead or a black sesame oil bottle in running water on Saturday. Keep a solid silver square in the pocket to avoid deceptive litigation and maternal disputes.",
    "Ketu_6": "Donate a black and white blanket on Tuesday. Feed street dogs regularly to prevent mysterious health ailments and disputes with maternal uncles.",
    "Sun (Surya)_6": "Offer jaggery and wheat to a red cow on Sunday. Donate medicines to a hospital to prevent chronic health issues and conflicts with authorities.",
    "Saturn (Shani)_7": "Do not build a house before age 48. Pour mustard oil on the floor on Saturday to prevent marital discord.",
    "Mars (Mangal)_7": "Donate red lentils on Tuesday. Do not keep weapons in the bedroom to prevent marital violence.",
    "Rahu_7": "Keep a silver square in pocket. Do not accept electrical items as gifts to prevent marital deception.",
    "Ketu_7": "Feed street dogs daily. Do not keep fragmented items in the bedroom to prevent marital separation.",
    "Sun (Surya)_7": "Offer water to the Sun daily. Do not consume salt on Sundays to maintain marital peace.",
    "Saturn (Shani)_8": "Do not build a house before age 48. Drop 8 kilograms of raw coal in running water on a Saturday to prevent hospitalization.",
    "Mars (Mangal)_8": "Feed sweet bread (roti) to a red dog on Tuesday. Keep a square piece of red copper in the house to prevent sudden trauma.",
    "Rahu_8": "Keep a solid silver square piece in the pocket. Float four coconuts in a river on Saturday to mitigate sudden litigation.",
    "Ketu_8": "Donate a black and white blanket. Feed street dogs regularly to prevent genetic health complications.",
    "Sun (Surya)_8": "Offer jaggery and wheat to a red cow on Sunday. Keep a copper pot filled with water in the bedroom at night and pour it into a plant in the morning.",
    "Saturn (Shani)_10": "Do not consume non-veg on Saturday. Feed black crows to prevent career stagnation.",
    "Mars (Mangal)_10": "Donate red lentils on Tuesday. Do not keep weapons in the office to prevent career conflicts.",
    "Rahu_10": "Keep a silver square in pocket. Do not accept electrical items as gifts to prevent career deception.",
    "Ketu_10": "Feed street dogs daily. Do not wear fragmented jewelry to prevent career instability.",
    "Sun (Surya)_10": "Offer water to the Sun daily. Do not consume salt on Sundays to maintain career status.",
    "Saturn (Shani)_12": "Keep a square piece of silver in pocket. Do not consume alcohol or non-vegetarian food on Saturdays to prevent insomnia.",
    "Mars (Mangal)_12": "Float a piece of red copper in flowing water on Tuesday. Do not keep weapons in the bedroom to prevent night terrors.",
    "Rahu_12": "Donate a black blanket to a homeless person. Keep a dog as a pet to absorb environmental malefic energy.",
    "Ketu_12": "Bury a pair of ivory pieces in a graveyard or at a crossroad. Avoid wearing fragmented or broken jewelry.",
    "Sun (Surya)_12": "Keep a copper coin in a visible spot in the house. Do not consume salt on Sundays to prevent immune system collapse."
}

# ==========================================
# DATABASE MANAGER (SQLite Stateless Architecture)
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

def safe_get(data, keys, default="*Data Unavailable*"):
    if not isinstance(data, dict): return default
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else: return default
    return current if current else default

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

def fmt_jd_to_mon_year(jd):
    y, m, d = swe.revjul(jd)[:3]
    return f"{m:02d}/{y}"

def calculate_vimshottari_timeline(moon_lon, birth_dt):
    nak_span = 360.0 / 27.0
    nak_idx, _, _, rem = get_nakshatra_info(moon_lon)
    lord_idx = (nak_idx // 3) % 9
    
    fraction_elapsed = rem / nak_span
    fraction_remaining = 1.0 - fraction_elapsed
    
    birth_jd = swe.julday(birth_dt.year, birth_dt.month, birth_dt.day)
    days_per_year = 365.25
    now_jd = swe.julday(datetime.now().year, datetime.now().month, datetime.now().day)
    
    curr_m_idx = lord_idx
    curr_m_years = DASHA_LORDS[curr_m_idx][1] * fraction_remaining
    curr_m_start_jd = birth_jd
    
    while True:
        curr_m_end_jd = curr_m_start_jd + (curr_m_years * days_per_year)
        if curr_m_end_jd > now_jd:
            m_lord = DASHA_LORDS[curr_m_idx][0]
            
            a_idx = curr_m_idx
            a_years = (DASHA_LORDS[a_idx][1] * DASHA_LORDS[curr_m_idx][1]) / 120.0
            if curr_m_idx == lord_idx: a_years *= fraction_remaining
            a_start_jd = curr_m_start_jd
            
            while True:
                a_end_jd = a_start_jd + (a_years * days_per_year)
                if a_end_jd > now_jd:
                    a_lord = DASHA_LORDS[a_idx][0]
                    
                    pa_idx = a_idx
                    pa_years = (DASHA_LORDS[pa_idx][1] * DASHA_LORDS[a_idx][1] * DASHA_LORDS[curr_m_idx][1]) / (120.0 * 120.0)
                    if curr_m_idx == lord_idx and a_idx == lord_idx: pa_years *= fraction_remaining
                    pa_start_jd = a_start_jd
                    
                    while True:
                        pa_end_jd = pa_start_jd + (pa_years * days_per_year)
                        if pa_end_jd > now_jd:
                            pa_lord = DASHA_LORDS[pa_idx][0]
                            
                            next_a_idx = (a_idx + 1) % 9
                            next_a_years = (DASHA_LORDS[next_a_idx][1] * DASHA_LORDS[curr_m_idx][1]) / 120.0
                            next_a_start_jd = a_end_jd
                            next_a_end_jd = next_a_start_jd + (next_a_years * days_per_year)
                            
                            return f"Current AD: {m_lord}-{a_lord} [{fmt_jd_to_mon_year(a_start_jd)} to {fmt_jd_to_mon_year(a_end_jd)}] | Current PAD: {pa_lord} [{fmt_jd_to_mon_year(pa_start_jd)} to {fmt_jd_to_mon_year(pa_end_jd)}] | Next AD: {m_lord}-{DASHA_LORDS[next_a_idx][0]} [{fmt_jd_to_mon_year(next_a_start_jd)} to {fmt_jd_to_mon_year(next_a_end_jd)}]"
                        
                        pa_start_jd = pa_end_jd
                        pa_idx = (pa_idx + 1) % 9
                        pa_years = (DASHA_LORDS[pa_idx][1] * DASHA_LORDS[a_idx][1] * DASHA_LORDS[curr_m_idx][1]) / (120.0 * 120.0)
                        
                a_start_jd = a_end_jd
                a_idx = (a_idx + 1) % 9
                a_years = (DASHA_LORDS[a_idx][1] * DASHA_LORDS[curr_m_idx][1]) / 120.0
                
        curr_m_start_jd = curr_m_end_jd
        curr_m_idx = (curr_m_idx + 1) % 9
        curr_m_years = DASHA_LORDS[curr_m_idx][1]

def calculate_charadasha(asc_sign, planets_full):
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    sign_lords = {"Aries": "Mars (Mangal)", "Taurus": "Venus (Shukra)", "Gemini": "Mercury (Budh)", "Cancer": "Moon (Chandra)", "Leo": "Sun (Surya)", "Virgo": "Mercury (Budh)", "Libra": "Venus (Shukra)", "Scorpio": "Mars (Mangal)", "Sagittarius": "Jupiter (Guru)", "Capricorn": "Saturn (Shani)", "Aquarius": "Saturn (Shani)", "Pisces": "Jupiter (Guru)"}
    
    if asc_idx in [0, 3, 6, 9]: start_idx = asc_idx 
    elif asc_idx in [1, 4, 7, 10]: start_idx = (asc_idx + 8) % 12 
    else: start_idx = (asc_idx + 4) % 12 
    
    ninth_idx = (asc_idx + 8) % 12
    direction = 1 if (ninth_idx % 2 == 0) else -1 
    
    dashas = []
    curr_idx = start_idx
    for _ in range(3):
        sign_name = ZODIAC_SIGNS[curr_idx]
        lord = sign_lords.get(sign_name)
        lord_sign = planets_full.get(lord, {}).get("sign")
        lord_idx = ZODIAC_SIGNS.index(lord_sign) if lord_sign else curr_idx
        
        if curr_idx == lord_idx: duration = 12
        else:
            duration = abs((lord_idx - curr_idx) * direction) % 12
            if duration == 0: duration = 12
            
        dashas.append(f"{sign_name} ({duration}y)")
        curr_idx = (curr_idx + direction) % 12
        
    return " -> ".join(dashas)

def calculate_transit_timings():
    now_dt = datetime.now()
    swe.set_ephe_path(None); swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    dt_utc = now_dt - timedelta(hours=5, minutes=30)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0)
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    
    planets_to_track = {"Saturn": swe.SATURN, "Jupiter": swe.JUPITER, "Rahu": swe.MEAN_NODE}
    timings = []
    
    for name, p_id in planets_to_track.items():
        calc = swe.calc_ut(jdut, p_id, flags)
        lon = calc[0][0] if isinstance(calc[0], tuple) else calc[0]
        curr_sign = int(lon / 30) % 12
        
        scan_jd = jdut
        for _ in range(730):
            scan_jd += 1.0
            calc_scan = swe.calc_ut(scan_jd, p_id, flags)
            lon_scan = calc_scan[0][0] if isinstance(calc_scan[0], tuple) else calc_scan[0]
            scan_sign = int(lon_scan / 30) % 12
            
            if scan_sign != curr_sign:
                ingress_date = swe.revjul(scan_jd)
                timings.append(f"{name} enters {HINDI_SIGNS[ZODIAC_SIGNS[scan_sign]]} on {ingress_date[1]:02d}/{ingress_date[0]}")
                break
                
    return "; ".join(timings) if timings else "No major ingress in next 2 years"

def calculate_transit_bav(natal_moon_sign, natal_asc_sign, houses_dict):
    now_dt = datetime.now()
    swe.set_ephe_path(None); swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    dt_utc = now_dt - timedelta(hours=5, minutes=30)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60.0)
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    
    t_sat = swe.calc_ut(jdut, swe.SATURN, flags); sat_lon = t_sat[0][0] if isinstance(t_sat[0], tuple) else t_sat[0]
    t_jup = swe.calc_ut(jdut, swe.JUPITER, flags); jup_lon = t_jup[0][0] if isinstance(t_jup[0], tuple) else t_jup[0]
    
    sat_sign = ZODIAC_SIGNS[int(sat_lon / 30) % 12]
    jup_sign = ZODIAC_SIGNS[int(jup_lon / 30) % 12]
    
    sat_house_moon = ((ZODIAC_SIGNS.index(sat_sign) - ZODIAC_SIGNS.index(natal_moon_sign)) % 12) + 1
    sat_house_asc = ((ZODIAC_SIGNS.index(sat_sign) - ZODIAC_SIGNS.index(natal_asc_sign)) % 12) + 1
    jup_house_moon = ((ZODIAC_SIGNS.index(jup_sign) - ZODIAC_SIGNS.index(natal_moon_sign)) % 12) + 1
    jup_house_asc = ((ZODIAC_SIGNS.index(jup_sign) - ZODIAC_SIGNS.index(natal_asc_sign)) % 12) + 1
    
    sat_bav_moon = calculate_bav("Saturn (Shani)", sat_house_moon, houses_dict)
    sat_bav_asc = calculate_bav("Saturn (Shani)", sat_house_asc, houses_dict)
    jup_bav_moon = calculate_bav("Jupiter (Guru)", jup_house_moon, houses_dict)
    jup_bav_asc = calculate_bav("Jupiter (Guru)", jup_house_asc, houses_dict)
    
    sat_friction = "Severe Friction" if sat_bav_moon <= 2 else "High Relief" if sat_bav_moon >= 6 else "Neutral"
    jup_relief = "High Relief" if jup_bav_moon >= 6 else "Low Relief" if jup_bav_moon <= 2 else "Neutral"
    
    return f"Saturn in {HINDI_SIGNS[sat_sign]} (H{sat_house_moon} from Moon, BAV:{sat_bav_moon}/8 - {sat_friction}; H{sat_house_asc} from Lagna, BAV:{sat_bav_asc}/8). Jupiter in {HINDI_SIGNS[jup_sign]} (H{jup_house_moon} from Moon, BAV:{jup_bav_moon}/8 - {jup_relief}; H{jup_house_asc} from Lagna, BAV:{jup_bav_asc}/8)."

def get_lal_kitab_remedy(houses_dict, planets_dict):
    remedies = []
    for p_name, p_data in planets_dict.items():
        if p_data.get("combust"):
            key = f"{p_name}_Combust"
            if key in LAL_KITAB_DICT: remedies.append(f"{p_name} is Combust: {LAL_KITAB_DICT[key]}")
        if p_data.get("dignity", "").startswith("Debilitated"):
            key = f"{p_name}_Debilitated"
            if key in LAL_KITAB_DICT: remedies.append(f"{p_name} is Debilitated: {LAL_KITAB_DICT[key]}")
                    
    for h_num in range(1, 13):
        occ = houses_dict[h_num]["occupants"]
        malefics_in_house = [p for p in occ if p in ["Saturn (Shani)", "Mars (Mangal)", "Rahu", "Ketu", "Sun (Surya)"]]
        for p_name in malefics_in_house:
            key = f"{p_name}_{h_num}"
            if key in LAL_KITAB_DICT: 
                remedy_text = LAL_KITAB_DICT[key]
                if len(malefics_in_house) > 1:
                    remedy_text += " (Warning: Malefic conjunction detected. Do not perform gemstone therapy for these planets.)"
                remedies.append(f"{p_name} in House {h_num}: {remedy_text}")
                        
    unique_remedies = list(dict.fromkeys(remedies))
    return unique_remedies[:5]

def detect_yogas(houses_dict, planets_dict, sign_lords):
    yogas = []
    moon_house = get_house_of_planet(houses_dict, "Moon (Chandra)")
    jup_house = get_house_of_planet(houses_dict, "Jupiter (Guru)")
    
    if moon_house and jup_house:
        if abs(jup_house - moon_house) in [0, 3, 6, 9]:
            yogas.append("Gaja Kesari Yoga (Jupiter in Kendra from Moon): Grants high intelligence, fame, wealth, strong moral character.")

    for p_name, p_data in planets_dict.items():
        if p_data.get("dignity", "").startswith("Debilitated"):
            deb_sign = p_data["sign"]
            exalt_lord = sign_lords.get(EXALTATION.get(p_name, ""))
            deb_lord = sign_lords.get(deb_sign, "")
            for lord in [exalt_lord, deb_lord]:
                if lord:
                    lord_house = get_house_of_planet(houses_dict, lord)
                    if lord_house in [1, 4, 7, 10]:
                        yogas.append(f"Neecha Bhanga Raja Yoga for {p_name}: Debilitation canceled by {lord} in Kendra. The initial weakness transforms into immense late-life power.")
                        break

    kendra_houses = [1, 4, 7, 10]
    trikona_houses = [1, 5, 9]
    kendra_lords = [sign_lords.get(houses_dict[h]["sign"], "") for h in kendra_houses]
    trikona_lords = [sign_lords.get(houses_dict[h]["sign"], "") for h in trikona_houses]
    
    for h_num in range(1, 13):
        occupants = houses_dict[h_num]["occupants"]
        for k_lord in kendra_lords:
            for t_lord in trikona_lords:
                if k_lord and t_lord and k_lord != t_lord:
                    if k_lord in occupants and t_lord in occupants:
                        yogas.append(f"Raja Yoga ({k_lord} conjunct {t_lord} in House {h_num}): Grants sudden elevation in status, power, and financial capacity.")
    return yogas

def calculate_chart_logic(asc_sign, planets_full, birth_dt):
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

    fact_sheet = "[GLOBAL PLANETARY INTERCONNECTION MATRIX]\n"
    for h, data in houses.items():
        occ_str = ', '.join(data['occupants']) if data['occupants'] else 'Empty'
        asp_str = ', '.join(data['aspected_by']) if data['aspected_by'] else 'None'
        fact_sheet += f"- House {h} ({data['hindi_sign']}): Occ: {occ_str}. Asp: {asp_str}.\n"
    
    logic_summary = f"[LIFE STAGE FILTER]: {life_stage}\n{fact_sheet}"
    
    dasha_timeline = calculate_vimshottari_timeline(planets_full["Moon (Chandra)"]["lon"], birth_dt)
    logic_summary += f"\n[VIMSHOTTARI TIMELINE]: {dasha_timeline}"
    
    charadasha = calculate_charadasha(asc_sign, planets_full)
    logic_summary += f"\n[JAIMINI CHARADASHA]: {charadasha}"
    
    transit_ingress = calculate_transit_timings()
    logic_summary += f"\n[TRANSIT INGRESS DATES]: {transit_ingress}"
    
    transit_bav = calculate_transit_bav(planets_full["Moon (Chandra)"]["sign"], asc_sign, houses)
    logic_summary += f"\n[CURRENT TRANSIT BAV]: {transit_bav}"

    asc_dosha = DOSHA_MAP.get(asc_sign, "Unknown")
    moon_dosha = DOSHA_MAP.get(planets_full["Moon (Chandra)"]["sign"], "Unknown")
    logic_summary += f"\n[AYURVEDIC DOSHA]: Ascendant is {asc_dosha}, Moon is {moon_dosha}."

    yogas = detect_yogas(houses, planets_full, sign_lords)
    logic_summary += f"\n[DETECTED YOGAS (KARMIC ASSETS)]:\n - " + "\n - ".join(yogas) if yogas else "\n[DETECTED YOGAS]: None."
    
    lal_kitab_rules = get_lal_kitab_remedy(houses, planets_full)
    logic_summary += f"\n[MANDATORY LAL KITAB REFERENCE]:\n - " + "\n - ".join(lal_kitab_rules) if lal_kitab_rules else "\n[MANDATORY LAL KITAB REFERENCE]: None."

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
    logic_breakdown, age = calculate_chart_logic(asc_sign, positions, dt_ist)
    
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

def call_groq_agent(groq_key, groq_url, model_name, system_msg, user_msg, json_mode=False):
    payload = {
        "model": model_name, 
        "messages": [
            {"role": "system", "content": system_msg}, 
            {"role": "user", "content": user_msg}
        ], 
        "temperature": 0.3
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
        
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
    try:
        res = requests.post(groq_url, headers=headers, json=payload, timeout=180)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        return json.dumps({"error": "API_ERROR", "details": res.text[:100]}) if json_mode else "[ERROR IN AGENT]"
    except Exception as e:
        return json.dumps({"error": "TIMEOUT", "details": str(e)}) if json_mode else "[AGENT TIMEOUT]"

def llm_output_firewall(text):
    replacements = {
        r"\bpotentially\b": "", r"\bpossibly\b": "", r"\bsuggesting that\b": "indicating that",
        r"\bsuggests that\b": "indicates that", r"\bsuggests a need\b": "mandates a need",
        r"\bassuming\b": "", r"\bself-care\b": "tactical remediation", r"\bdate nights\b": "structured relational protocols",
        r"\byoga\b": "Ayurvedic physical routines", r"\bmeditation\b": "targeted mantric resonance",
        r"\bmindfulness\b": "clinical situational awareness"
    }
    clean_text = text
    for pattern, replacement in replacements.items():
        clean_text = re.compile(pattern, re.IGNORECASE).sub(replacement, clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def generate_pdf_weasyprint(html_content, pdf_path):
    try:
        HTML(string=html_content).write_pdf(pdf_path)
        return True
    except Exception as e:
        print(f"WEASYPRINT ERROR: {e}", flush=True)
        return False

def process_background_task(chat_id, session_data):
    groq_key = os.environ.get("GROQ_API_KEY")
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    
    # MANDATE: EXACT MODEL STRINGS TO BYPASS TIER RESTRICTIONS
    # Replaced llama-3.3-70b-versatile with llama3-70b-8192 for tier stability
    MASTER_MODEL = "llama3-70b-8192"
    TRANSLATOR_MODEL = "mixtral-8x7b-32768"
    
    send_message(chat_id, "⏳ Initiating Structural Integrity Audit Pipeline...")
    
    system_msg = """You are an Elite Vedic Astrological Auditor. This is an AUDIT, not an appraisal. Negatives and Threats MUST be stated first and bluntly. Do not snub the bad to highlight the good.
[ABSOLUTE LAWS - VIOLATION = FAILURE]
1. THREAT-FIRST SEQUENCING: For every key inside "structural_analysis", you MUST format the text using a strict bulleted list (do not merge into a paragraph). Follow this exact sequence:
   - **The Warning (Threat First):** State the severe afflictions (Combust, Debilitated, low BAV, malefic aspect) and the exact timeline of the threat. Do not sugarcoat.
   - **The Support (Karmic Asset):** State the positive placements (Exalted, high BAV, Yogas) that will act as a shield during the affected phase.
   - **The Synthesis:** Explain exactly how the native must combine the Support to survive the Warning.
2. AFFLICTION MANDATE: If a planet is Combust, Retrograde, or Debilitated, you MUST explicitly state how that specific state modifies the house it sits in. Do not ignore afflictions just because an asset (like a Raja Yoga) is present.
3. TIMELINE MANDATE: You must cite exact dates when discussing predictions.
4. AYURVEDIC ACCURACY: In the "ayurvedic_audit", you MUST diagnose the exact physical Dosha (Vata/Pitta/Kapha) based on the provided [AYURVEDIC DOSHA] data and prescribe specific dietary/lifestyle shifts.
5. CONSOLIDATED UPAYAS: In the "remediation_protocol" object, you must output two distinct sub-sections as strings:
   A. "suppressing_afflictions": Inject the exact, hardcoded Lal Kitab remedies provided in the [MANDATORY LAL KITAB REFERENCE] here, alongside specific Daan (donations) for the current malefic transits/dashas.
   B. "amplifying_assets": Recommend specific Gemstones (Ratnas), Beej Mantras, or lifestyle alignments to amplify the positive Karmic Assets identified in the Support sections.
6. FORBIDDEN CONCEPTS: Do not use 'potentially', 'possibly', 'suggesting', 'assuming', 'yoga' (the physical exercise), 'meditation'. Use definitive clinical terms.
7. HINDI MANDATORY: Use Hindi names for EVERY Zodiac Sign and Planet.
8. JSON OUTPUT STRICTLY ENFORCED: Output ONLY a valid JSON object matching the exact schema provided.
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
Generate the JSON object based strictly on the provided data. 
The JSON must match this exact schema:
{{
  "temporal_narrative": {{
    "psychological_baseline": "...",
    "historical_trajectory": "...",
    "present_trigger": "...",
    "expected_survival": "..."
  }},
  "structural_analysis": {{
    "wealth_and_career": "...",
    "relationships_and_property": "...",
    "vitality_and_subconscious": "..."
  }},
  "ayurvedic_audit": "...",
  "remediation_protocol": {{
    "suppressing_afflictions": "...",
    "amplifying_assets": "..."
  }}
}}
"""
    
    # 1. Master Synthesizer Agent (English JSON Generation)
    english_json_str = call_groq_agent(groq_key, groq_url, MASTER_MODEL, system_msg, user_msg_eng, json_mode=True)
    
    english_json_str = english_json_str.strip()
    if english_json_str.startswith("```json"):
        english_json_str = english_json_str[7:]
    elif english_json_str.startswith("```"):
        english_json_str = english_json_str[3:]
    if english_json_str.endswith("```"):
        english_json_str = english_json_str[:-3]
    english_json_str = english_json_str.strip()

    try:
        eng_data = json.loads(english_json_str)
        if "error" in eng_data:
            send_message(chat_id, f"⚠️ Master Agent API Error: {eng_data.get('details', 'Unknown Error')}")
            return
    except json.JSONDecodeError:
        send_message(chat_id, "⚠️ JSON Parsing failed from Master Agent. Check server logs.")
        print(f"JSON PARSE FAIL. RAW OUTPUT:\n{english_json_str[:2000]}", flush=True)
        return

    for k, v in eng_data.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                eng_data[k][sub_k] = llm_output_firewall(sub_v)
        else:
            eng_data[k] = llm_output_firewall(v)

    translator_system_msg = """You are an expert astrological translator. Translate the provided English JSON object into Hindi. 
    CRITICAL: You are translating a JSON object. You MUST NOT translate the JSON keys. The keys must remain exactly in English (e.g., 'wealth_and_career'). Only translate the string values into Hindi. 
    Output ONLY a valid JSON object with the EXACT SAME ENGLISH KEYS. 
    DO NOT put Hindi words in brackets if they are already in Devanagari script. Translate exactly."""
    
    # 2. Translator Agent (Hindi Translation)
    hindi_json_str = call_groq_agent(groq_key, groq_url, TRANSLATOR_MODEL, translator_system_msg, json.dumps(eng_data), json_mode=True)
    
    try:
        hin_data = json.loads(hindi_json_str)
    except json.JSONDecodeError:
        hin_data = {"error": "Hindi translation failed."}

    def md_to_html(text):
        return markdown2.markdown(str(text), extras=["fenced-code-blocks"])

    html_body = f"""
    <h1>Astrological Audit</h1>
    <p><em>Disclaimer: This audit maps karmic tendencies, assets, and probabilistic risk vectors based on planetary mathematics.</em></p>
    
    <h2>I. THE TEMPORAL-PSYCHOLOGICAL NARRATIVE</h2>
    <h3>The Psychological Baseline</h3>
    {md_to_html(safe_get(eng_data, ["temporal_narrative", "psychological_baseline"]))}
    <h3>The Historical Trajectory</h3>
    {md_to_html(safe_get(eng_data, ["temporal_narrative", "historical_trajectory"]))}
    <h3>The Present Trigger</h3>
    {md_to_html(safe_get(eng_data, ["temporal_narrative", "present_trigger"]))}
    <h3>The Expected State & Survival</h3>
    {md_to_html(safe_get(eng_data, ["temporal_narrative", "expected_survival"]))}
    
    <h2>II. STRUCTURAL INTEGRITY ANALYSIS</h2>
    <h3>Pillar 1: Wealth, Career & Structural Stability</h3>
    {md_to_html(safe_get(eng_data, ["structural_analysis", "wealth_and_career"]))}
    <h3>Pillar 2: Relationship, Property & Progeny Dynamics</h3>
    {md_to_html(safe_get(eng_data, ["structural_analysis", "relationships_and_property"]))}
    <h3>Pillar 3: Core Vitality & Subconscious Trajectory</h3>
    {md_to_html(safe_get(eng_data, ["structural_analysis", "vitality_and_subconscious"]))}
    
    <h2>III. AYURVEDIC & NEUROLOGICAL AUDIT</h2>
    {md_to_html(safe_get(eng_data, ["ayurvedic_audit"]))}
    
    <h2>IV. CONSOLIDATED UPAYAS (REMEDICATION PROTOCOL)</h2>
    <h3>A. Suppressing Afflictions</h3>
    {md_to_html(safe_get(eng_data, ["remediation_protocol", "suppressing_afflictions"]))}
    <h3>B. Amplifying Assets</h3>
    {md_to_html(safe_get(eng_data, ["remediation_protocol", "amplifying_assets"]))}
    """
    
    if "error" not in hin_data:
        html_body += f"""
        <div style="page-break-before: always;"></div>
        <h1>भाग 2: हिंदी अनुवाद (HINDI TRANSLATION)</h1>
        
        <h2>I. काल-मानसिक कथा (मूल निदान)</h2>
        <h3>मानसिक आधार</h3>
        {md_to_html(safe_get(hin_data, ["temporal_narrative", "psychological_baseline"]))}
        <h3>ऐतिहासिक प्रक्षेपपथ</h3>
        {md_to_html(safe_get(hin_data, ["temporal_narrative", "historical_trajectory"]))}
        <h3>वर्तमान ट्रिगर</h3>
        {md_to_html(safe_get(hin_data, ["temporal_narrative", "present_trigger"]))}
        <h3>अपेक्षित स्थिति और जीवित रहना</h3>
        {md_to_html(safe_get(hin_data, ["temporal_narrative", "expected_survival"]))}
        
        <h2>II. संरचनात्मक अखंडता विश्लेषण</h2>
        <h3>पिलर 1: धन, करियर और संरचनात्मक स्थिरता</h3>
        {md_to_html(safe_get(hin_data, ["structural_analysis", "wealth_and_career"]))}
        <h3>पिलर 2: संबंध, संपत्ति और संतान गतिशीलता</h3>
        {md_to_html(safe_get(hin_data, ["structural_analysis", "relationships_and_property"]))}
        <h3>पिलर 3: मूल विटैलिटी और अवचेतन प्रक्षेपपथ</h3>
        {md_to_html(safe_get(hin_data, ["structural_analysis", "vitality_and_subconscious"]))}
        
        <h2>III. आयुर्वेदिक और तंत्रिका विज्ञान ऑडिट</h2>
        {md_to_html(safe_get(hin_data, ["ayurvedic_audit"]))}
        
        <h2>IV. समेकित उपाय (रेमेडिएशन प्रोटोकॉल)</h2>
        <h3>अ. दोषों का दमन</h3>
        {md_to_html(safe_get(hin_data, ["remediation_protocol", "suppressing_afflictions"]))}
        <h3>ब. संपत्तियों का प्रवर्धन</h3>
        {md_to_html(safe_get(hin_data, ["remediation_protocol", "amplifying_assets"]))}
        """

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
    
    send_message(chat_id, "⏳ Compiling Forensic Dossier PDF...")
    file_tag = str(int(time.time()))
    pdf_path = f"/tmp/Astrological_Audit_{file_tag}.pdf"
    
    if generate_pdf_weasyprint(full_html, pdf_path) and os.path.exists(pdf_path):
        send_document(chat_id, pdf_path)
        send_message(chat_id, "📄 **Astrological Audit PDF attached above!** ⬆️")
    else:
        send_message(chat_id, "⚠️ PDF generation failed. Sending text report:")
        for k, v in eng_data.items():
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    send_message(chat_id, f"{sub_k.replace('_', ' ').title()}:\n{sub_v}")
            else:
                send_message(chat_id, f"{k.replace('_', ' ').title()}:\n{v}")

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

            # ==========================================
            # BRAND NEW USERS BLOCK (STATE 0 SECURED)
            # ==========================================
            elif match:
                day, month, year, hour, minute, city_input = match.groups()
                day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                if year < 100: year += 1900 if year > 25 else 2000
                
                send_message(chat_id, "⏳ Calculating...")
                
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
                    "state": "ready_to_generate",
                    "asc_sign": asc_sign, "planet_summary": planet_summary,
                    "planet_data": planets, "logic_breakdown": logic_breakdown, "age": age,
                    "birth_str": f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean} (Age: {age})"
                }
                save_session(chat_id, session)
                
                threading.Thread(target=process_background_task, args=(chat_id, session)).start()
                return jsonify(status="success"), 200

            elif session and session.get("state") == "awaiting_partner" and user_text.lower() == 'skip':
                session["state"] = "ready_to_generate"
                save_session(chat_id, session)
                threading.Thread(target=process_background_task, args=(chat_id, session)).start()
                return jsonify(status="success"), 200
                
            elif session and session.get("state") == "ready_to_generate":
                send_message(chat_id, "Running follow-up analysis...")
                groq_key = os.environ.get("GROQ_API_KEY")
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                
                q_system_msg = """You are an Elite Vedic Astrological Auditor. Answer the user's follow-up question directly based on the provided chart data. 
                THREAT-FIRST: State the negative/vulnerability first, then the supporting asset. Cite exact dates. Do not use fluff words. Use Hindi names."""
                
                q_prompt = f"[CHART DATA]\n{session['logic_breakdown']}\n[USER QUESTION]\n{user_text}"
                # Replaced decommissioned models with highly accessible llama3-70b-8192
                payload = {"model": "llama3-70b-8192", "messages": [{"role": "system", "content": q_system_msg}, {"role": "user", "content": q_prompt}], "temperature": 0.3}
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
