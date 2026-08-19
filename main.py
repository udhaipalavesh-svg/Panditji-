# ==========================================
# CORE IMPORTS & APP INITIALIZATION
# ==========================================
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
# CORE ASTROLOGY CONSTANTS & MATH TABLES
# ==========================================
ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
HINDI_SIGNS = {"Aries": "Aries / Mesha", "Taurus": "Taurus / Vrishabha", "Gemini": "Gemini / Mithuna", "Cancer": "Cancer / Karka", "Leo": "Leo / Simha", "Virgo": "Virgo / Kanya", "Libra": "Libra / Tula", "Scorpio": "Scorpio / Vrishchika", "Sagittarius": "Sagittarius / Dhanu", "Capricorn": "Capricorn / Makara", "Aquarius": "Aquarius / Kumbha", "Pisces": "Pisces / Meena"}
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
DASHA_LORDS = [("Ketu / Ketu", 7), ("Venus / Shukra", 20), ("Sun / Surya", 6), ("Moon / Chandra", 10), ("Mars / Mangal", 7), ("Rahu / Rahu", 18), ("Jupiter / Guru", 16), ("Saturn / Shani", 19), ("Mercury / Budh", 17)]
EXALTATION = {"Sun / Surya": "Aries", "Moon / Chandra": "Taurus", "Mars / Mangal": "Capricorn", "Mercury / Budh": "Virgo", "Jupiter / Guru": "Cancer", "Venus / Shukra": "Pisces", "Saturn / Shani": "Libra", "Rahu / Rahu": "Taurus", "Ketu / Ketu": "Scorpio"}
DEBILITATION = {"Sun / Surya": "Libra", "Moon / Chandra": "Scorpio", "Mars / Mangal": "Cancer", "Mercury / Budh": "Pisces", "Jupiter / Guru": "Capricorn", "Venus / Shukra": "Virgo", "Saturn / Shani": "Aries", "Rahu / Rahu": "Scorpio", "Ketu / Ketu": "Taurus"}
OWN_SIGNS = {"Sun / Surya": ["Leo"], "Moon / Chandra": ["Cancer"], "Mars / Mangal": ["Aries", "Scorpio"], "Mercury / Budh": ["Gemini", "Virgo"], "Jupiter / Guru": ["Sagittarius", "Pisces"], "Venus / Shukra": ["Taurus", "Libra"], "Saturn / Shani": ["Capricorn", "Aquarius"]}
COMBUSTION_ORB = {"Moon / Chandra": 12, "Mars / Mangal": 17, "Mercury / Budh": 14, "Jupiter / Guru": 11, "Venus / Shukra": 10, "Saturn / Shani": 15}
NAK_LORDS = ["Ketu / Ketu", "Venus / Shukra", "Sun / Surya", "Moon / Chandra", "Mars / Mangal", "Rahu / Rahu", "Jupiter / Guru", "Saturn / Shani", "Mercury / Budh"]
DOSHA_MAP = {"Aries": "Pitta", "Taurus": "Kapha", "Gemini": "Vata", "Cancer": "Kapha", "Leo": "Pitta", "Virgo": "Vata", "Libra": "Vata", "Scorpio": "Kapha", "Sagittarius": "Pitta", "Capricorn": "Vata", "Aquarius": "Vata", "Pisces": "Kapha"}

BAV_TABLES = {
    "Sun / Surya": [0,0,1,1,0,0,1,1, 1,0,0,0,1,1,0,0, 0,1,1,0,0,1,1,0, 0,0,1,1,0,0,1,1, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 0,0,0,1,1,1,1,0, 1,1,1,0,0,0,0,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0],
    "Moon / Chandra": [0,1,0,1,1,0,1,0, 1,0,1,0,0,1,0,1, 1,1,0,0,1,1,0,0, 0,1,1,0,1,0,1,0, 1,0,1,1,0,1,0,1, 0,1,0,1,1,0,1,0, 1,1,0,1,0,1,1,0, 0,0,1,1,1,1,0,0, 1,1,0,0,0,0,1,1, 0,0,1,1,1,1,0,0, 1,0,1,0,0,1,0,1, 0,1,0,1,1,0,1,0],
    "Mars / Mangal": [1,0,0,1,1,0,0,1, 1,1,0,0,1,1,0,0, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 0,1,1,0,1,0,1,0, 1,0,1,0,0,1,0,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,0,1,1,1,1,0],
    "Mercury / Budh": [0,1,1,0,1,0,0,1, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,1,0,0,1,1,0,0],
    "Jupiter / Guru": [0,1,1,1,0,0,0,0, 1,0,0,0,1,1,1,0, 1,1,0,0,0,0,1,1, 0,0,1,1,1,1,0,0, 1,1,1,0,0,0,0,1, 0,0,0,1,1,1,1,0, 0,1,1,0,1,0,1,0, 1,0,0,1,0,1,0,1, 0,1,1,1,0,0,0,0, 1,0,0,0,1,1,1,0, 0,0,0,1,1,1,1,0, 1,1,1,0,0,0,0,1],
    "Venus / Shukra": [1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 0,1,1,0,1,0,1,0, 1,0,0,1,0,1,0,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0],
    "Saturn / Shani": [0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,0,0,1,1,0, 0,1,0,1,1,0,0,1, 1,0,1,0,1,0,0,1, 0,1,0,1,0,1,1,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0]
}

LAL_KITAB_DICT = {
    "Saturn / Shani_Combust": "Donate black sesame oil on Saturday. Keep a square piece of silver in wallet to prevent liquid cash evaporation.",
    "Mars / Mangal_Combust": "Donate red masoor dal on Tuesday. Avoid keeping iron tools under the bed to prevent surgical interventions.",
    "Jupiter / Guru_Combust": "Donate turmeric and chana dal on Thursday. Apply a tilak of saffron on the forehead to stabilize intellect.",
    "Venus / Shukra_Combust": "Donate pure ghee to a temple on Friday. Feed wheat dough to a cow to stabilize marital harmony.",
    "Mercury / Budh_Combust": "Donate green moong dal on Wednesday. Clean teeth with fitkari (alum) daily to prevent nervous system burnout.",
    "Mars / Mangal_Debilitated": "Float a piece of red copper in a flowing river on Tuesday. Sleep on a white bedsheet to calm aggressive impulses.",
    "Sun / Surya_Debilitated": "Donate wheat and jaggery on Sunday. Offer water to the Sun (Surya Arghya) with a pinch of red sandalwood to rebuild self-worth.",
    "Moon / Chandra_Debilitated": "Immerse a square piece of silver in a flowing river on Monday. Feed wheat flour balls to fish to cure clinical anxiety.",
    "Venus / Shukra_Debilitated": "Donate white sweets to young girls on Friday. Keep a silver glass for drinking water to restore relationship balance.",
    "Jupiter / Guru_Debilitated": "Water a peepal tree on Thursday. Donate yellow clothes or books to a priest or student to clear karmic debts.",
    "Saturn / Shani_Debilitated": "Serve food to lepers or disabled people. Feed black dogs on Saturday to remove chronic structural obstacles.",
    "Saturn / Shani_1": "Do not consume non-veg on Saturday. Feed black crows daily to prevent chronic fatigue and identity erosion.",
    "Mars / Mangal_1": "Donate red lentils on Tuesday. Avoid keeping weapons in the house to prevent aggressive outbursts.",
    "Rahu / Rahu_1": "Keep a silver square in pocket. Do not accept electrical items as gifts to prevent identity confusion.",
    "Ketu / Ketu_1": "Feed street dogs daily. Do not wear fragmented jewelry to prevent scattered focus.",
    "Sun / Surya_1": "Offer water to the Sun daily. Do not consume salt on Sundays to maintain vitality.",
    "Saturn / Shani_2": "Keep a silver square in wallet. Serve food to disabled people to prevent wealth erosion.",
    "Mars / Mangal_2": "Donate red masoor dal on Tuesday. Do not keep iron tools in the kitchen to prevent family disputes.",
    "Rahu / Rahu_2": "Keep a solid silver ball in the mouth for a few minutes daily. Do not accept bribes to prevent wealth loss.",
    "Ketu / Ketu_2": "Donate a black and white blanket. Do not keep broken glass in the house to prevent wealth leakage.",
    "Sun / Surya_2": "Donate wheat and jaggery on Sunday. Do not consume hot food to prevent family arguments.",
    "Saturn / Shani_4": "Do not build a house before age 48. Pour mustard oil on the floor on Saturday to prevent domestic disputes.",
    "Mars / Mangal_4": "Keep a square piece of red copper in the house. Do not keep weapons under the bed to prevent domestic violence.",
    "Rahu / Rahu_4": "Keep a solid silver square in the house. Do not keep electronic items in the bedroom to prevent insomnia.",
    "Ketu / Ketu_4": "Feed street dogs daily. Do not keep fragmented items in the house to prevent domestic unrest.",
    "Sun / Surya_4": "Offer water to the Sun daily. Do not consume salt on Sundays to maintain domestic peace.",
    "Saturn / Shani_5": "Do not build a house before age 48. Feed black crows to prevent delays in progeny.",
    "Mars / Mangal_5": "Donate red lentils on Tuesday. Do not keep weapons in the bedroom to prevent miscarriages.",
    "Rahu / Rahu_5": "Keep a silver square in pocket. Do not accept electrical items as gifts to prevent progeny issues.",
    "Ketu / Ketu_5": "Feed street dogs daily. Do not wear fragmented jewelry to prevent progeny delays.",
    "Sun / Surya_5": "Offer water to the Sun daily. Do not consume salt on Sundays to maintain progeny health.",
    "Saturn / Shani_6": "Float a black mustard oil-filled bottle in a river on Saturday. Serve food to disabled people to ward off chronic debts and prolonged illnesses.",
    "Mars / Mangal_6": "Donate red masoor dal and batasha (sweet) on Tuesday. Feed a monkey or a red dog to neutralize enemies and prevent aggressive litigation.",
    "Rahu / Rahu_6": "Float a piece of lead or a black sesame oil bottle in running water on Saturday. Keep a solid silver square in the pocket to avoid deceptive litigation and maternal disputes.",
    "Ketu / Ketu_6": "Donate a black and white blanket on Tuesday. Feed street dogs regularly to prevent mysterious health ailments and disputes with maternal uncles.",
    "Sun / Surya_6": "Offer jaggery and wheat to a red cow on Sunday. Donate medicines to a hospital to prevent chronic health issues and conflicts with authorities.",
    "Saturn / Shani_7": "Do not build a house before age 48. Pour mustard oil on the floor on Saturday to prevent marital discord.",
    "Mars / Mangal_7": "Donate red lentils on Tuesday. Do not keep weapons in the bedroom to prevent marital violence.",
    "Rahu / Rahu_7": "Keep a silver square in pocket. Do not accept electrical items as gifts to prevent marital deception.",
    "Ketu / Ketu_7": "Feed street dogs daily. Do not keep fragmented items in the bedroom to prevent marital separation.",
    "Sun / Surya_7": "Offer water to the Sun daily. Do not consume salt on Sundays to maintain marital peace.",
    "Saturn / Shani_8": "Do not build a house before age 48. Drop 8 kilograms of raw coal in running water on a Saturday to prevent hospitalization.",
    "Mars / Mangal_8": "Feed sweet bread (roti) to a red dog on Tuesday. Keep a square piece of red copper in the house to prevent sudden trauma.",
    "Rahu / Rahu_8": "Keep a solid silver square piece in the pocket. Float four coconuts in a river on Saturday to mitigate sudden litigation.",
    "Ketu / Ketu_8": "Donate a black and white blanket. Feed street dogs regularly to prevent genetic health complications.",
    "Sun / Surya_8": "Offer jaggery and wheat to a red cow on Sunday. Keep a copper pot filled with water in the bedroom at night and pour it into a plant in the morning.",
    "Saturn / Shani_10": "Do not consume non-veg on Saturday. Feed black crows to prevent career stagnation.",
    "Mars / Mangal_10": "Donate red lentils on Tuesday. Do not keep weapons in the office to prevent career conflicts.",
    "Rahu / Rahu_10": "Keep a silver square in pocket. Do not accept electrical items as gifts to prevent career deception.",
    "Ketu / Ketu_10": "Feed street dogs daily. Do not wear fragmented jewelry to prevent career instability.",
    "Sun / Surya_10": "Offer water to the Sun daily. Do not consume salt on Sundays to maintain career status.",
    "Saturn / Shani_12": "Keep a square piece of silver in pocket. Do not consume alcohol or non-vegetarian food on Saturdays to prevent insomnia.",
    "Mars / Mangal_12": "Float a piece of red copper in flowing water on Tuesday. Do not keep weapons in the bedroom to prevent night terrors.",
    "Rahu / Rahu_12": "Donate a black blanket to a homeless person. Keep a dog as a pet to absorb environmental malefic energy.",
    "Ketu / Ketu_12": "Bury a pair of ivory pieces in a graveyard or at a crossroad. Avoid wearing fragmented or broken jewelry.",
    "Sun / Surya_12": "Keep a copper coin in a visible spot in the house. Do not consume salt on Sundays to prevent immune system collapse."
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
def calculate_vargas(natal_planets_dict):
    vargas = {}
    navamsha_start_map = [0, 9, 6, 3] 
    for planet, data in natal_planets_dict.items():
        lon = data.get("lon", 0.0) % 360.0
        sign_idx = int(lon // 30) % 12
        deg_in_sign = lon % 30
        
        navamsha_idx_in_sign = int(deg_in_sign // (30/9))
        navamsha_start_sign = navamsha_start_map[sign_idx % 4]
        d9_sign_idx = (navamsha_start_sign + navamsha_idx_in_sign) % 12
        d9_sign = ZODIAC_SIGNS[d9_sign_idx]
        
        dashamsha_idx_in_sign = int(deg_in_sign // 3)
        if sign_idx % 2 == 0:
            d10_sign_idx = (sign_idx + dashamsha_idx_in_sign) % 12
        else:
            d10_sign_idx = (sign_idx + 8 + dashamsha_idx_in_sign) % 12
        d10_sign = ZODIAC_SIGNS[d10_sign_idx]
        
        vargas[planet] = {"D9": d9_sign, "D10": d10_sign}
    return vargas

def calculate_full_sav(houses_dict):
    planets_for_sav = ["Sun / Surya", "Moon / Chandra", "Mars / Mangal", "Mercury / Budh", "Jupiter / Guru", "Venus / Shukra", "Saturn / Shani"]
    sav_scores = {}
    for house_num in range(1, 13):
        house_total = 0
        for planet in planets_for_sav:
            house_total += calculate_bav(planet, house_num, houses_dict)
        sav_scores[house_num] = house_total
    return sav_scores

def get_nakshatra_info(lon):
    nak_span = 360.0 / 27.0
    nak_idx = int(lon / nak_span) % 27
    rem = lon % nak_span
    pada = int(rem / (nak_span / 4.0)) + 1
    return nak_idx, NAKSHATRAS[nak_idx], pada, rem

def get_planet_dignity(planet, sign):
    if EXALTATION.get(planet) == sign: return "Exalted / Uchcha"
    if DEBILITATION.get(planet) == sign: return "Debilitated / Neecha"
    if planet in OWN_SIGNS and sign in OWN_SIGNS[planet]: return "Own Sign / Swavritti"
    return "Neutral"

def get_aspects(planet, house):
    aspects = [7]
    if planet == "Mars / Mangal": aspects.extend([4, 8])
    elif planet == "Jupiter / Guru": aspects.extend([5, 9])
    elif planet == "Saturn / Shani": aspects.extend([3, 10])
    elif planet in ["Rahu / Rahu", "Ketu / Ketu"]: aspects.extend([5, 9])
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

def get_lal_kitab_remedy(houses_dict, planets_dict):
    remedies = []
    for p_name, p_data in planets_dict.items():
        if p_data.get("combust"):
            key = f"{p_name}_Combust"
            if key in LAL_KITAB_DICT: remedies.append(f"{p_name} Combust: {LAL_KITAB_DICT[key]}")
        if p_data.get("dignity", "").startswith("Debilitated"):
            key = f"{p_name}_Debilitated"
            if key in LAL_KITAB_DICT: remedies.append(f"{p_name} Debilitated: {LAL_KITAB_DICT[key]}")
            
    for h_num in range(1, 13):
        occ = houses_dict[h_num]["occupants"]
        malefics_in_house = [p for p in occ if p in ["Saturn / Shani", "Mars / Mangal", "Rahu / Rahu", "Ketu / Ketu", "Sun / Surya"]]
        for p_name in malefics_in_house:
            key = f"{p_name}_{h_num}"
            if key in LAL_KITAB_DICT: 
                remedy_text = LAL_KITAB_DICT[key]
                if len(malefics_in_house) > 1:
                    remedy_text += " (Warning: Malefic conjunction detected. Do not perform gemstone therapy for these planets.)"
                remedies.append(f"{p_name} in House {h_num}: {remedy_text}")
                
    return list(dict.fromkeys(remedies))[:5]

def detect_yogas(houses_dict, planets_dict, sign_lords):
    yogas = []
    moon_house = get_house_of_planet(houses_dict, "Moon / Chandra")
    jup_house = get_house_of_planet(houses_dict, "Jupiter / Guru")
    
    if moon_house and jup_house:
        if abs(jup_house - moon_house) in [0, 3, 6, 9]:
            yogas.append("Gaja Kesari Yoga (Jupiter in Kendra from Moon): Grants high intelligence, fame, and robust moral fortitude.")
    return yogas

def calculate_chart_logic(asc_sign, planets_full, birth_dt):
    now = datetime.now()
    age = (now - birth_dt).days // 365
    life_stage = f"ESTABLISHMENT (Age {age}): Deep dive into House 10, 7, 2, 6." if age > 25 else f"YOUNG ADULT (Age {age})"

    sign_lords = {"Aries": "Mars / Mangal", "Taurus": "Venus / Shukra", "Gemini": "Mercury / Budh", "Cancer": "Moon / Chandra", "Leo": "Sun / Surya", "Virgo": "Mercury / Budh", "Libra": "Venus / Shukra", "Scorpio": "Mars / Mangal", "Sagittarius": "Jupiter / Guru", "Capricorn": "Saturn / Shani", "Aquarius": "Saturn / Shani", "Pisces": "Jupiter / Guru"}
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
    logic_summary += f"\n[VIMSHOTTARI TIMELINE]: {calculate_vimshottari_timeline(planets_full['Moon / Chandra']['lon'], birth_dt)}"
    logic_summary += f"\n[TRANSIT INGRESS DATES]: {calculate_transit_timings()}"

    yogas = detect_yogas(houses, planets_full, sign_lords)
    logic_summary += f"\n[DETECTED YOGAS]:\n - " + "\n - ".join(yogas) if yogas else "\n[DETECTED YOGAS]: None."
    
    logic_summary += f"\n[DIVISIONAL VARGAS (D-9 & D-10)]: {json.dumps(calculate_vargas(planets_full))}\n[FULL SARVASHTAKAVARGA (SAV) MATRIX]: {json.dumps(calculate_full_sav(houses))}"
    
    lal_rules = get_lal_kitab_remedy(houses, planets_full)
    logic_summary += f"\n[LAL KITAB RULES]:\n - " + "\n - ".join(lal_rules) if lal_rules else "\n[LAL KITAB RULES]: None applicable."

    return logic_summary, age

def calculate_sidereal_chart(day, month, year, hour, minute, lat, lon):
    swe.set_ephe_path(None); swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    dt_ist = datetime(year, month, day, hour, minute)
    dt_utc = dt_ist - timedelta(hours=5, minutes=30)
    utc_decimal = dt_utc.hour + (dt_utc.minute / 60.0)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal)
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    planets = {"Sun / Surya": swe.SUN, "Moon / Chandra": swe.MOON, "Mars / Mangal": swe.MARS, "Mercury / Budh": swe.MERCURY, "Jupiter / Guru": swe.JUPITER, "Venus / Shukra": swe.VENUS, "Saturn / Shani": swe.SATURN, "Rahu / Rahu": swe.MEAN_NODE, "Ketu / Ketu": 10}
    positions = {}; rahu_lon = 0.0; sun_lon = 0.0
    
    for name, p_id in planets.items():
        if name == "Ketu / Ketu": 
            lon_val = (rahu_lon + 180.0) % 360.0
        else:
            calc = swe.calc_ut(jdut, p_id, flags)
            lon_val = calc[0][0] if isinstance(calc, tuple) and isinstance(calc[0], tuple) else (calc[0] if isinstance(calc, tuple) else 0.0)
            if name == "Rahu / Rahu": rahu_lon = lon_val
            if name == "Sun / Surya": sun_lon = lon_val
            
        sign_idx = int(lon_val / 30) % 12; sign_name = ZODIAC_SIGNS[sign_idx]
        nak_idx, nak_name, _, _ = get_nakshatra_info(lon_val)
        
        positions[name] = {
            "sign": sign_name, "hindi_sign": HINDI_SIGNS[sign_name], "lon": lon_val % 360.0, 
            "nak": nak_name, "dignity": get_planet_dignity(name, sign_name),
            "combust": (abs(lon_val - sun_lon) < COMBUSTION_ORB.get(name, 0)) if name in COMBUSTION_ORB else False
        }
        
    try: _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags); asc_lon = ascmc[0] % 360.0
    except: asc_lon = 0.0
        
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]
    logic_breakdown, age = calculate_chart_logic(asc_sign, positions, dt_ist)
    return asc_sign, positions, logic_breakdown, age

# ==========================================
# VISUAL RENDERERS (PURE PYTHON SVG)
# ==========================================
def generate_cover_page_svg(native_name="Native", birth_str=""):
    return f"""
    <svg viewBox="0 0 800 1130" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: 100vh; font-family: 'Noto Sans', sans-serif;">
        <rect width="800" height="1130" fill="#fdfbf7" />
        <rect x="30" y="30" width="740" height="1070" fill="none" stroke="#4A154B" stroke-width="2" rx="12" />
        <rect x="40" y="40" width="720" height="1050" fill="none" stroke="#D4AF37" stroke-width="1" rx="8" />
        
        <text x="400" y="150" font-size="72" fill="#4A154B" text-anchor="middle" font-weight="bold">ॐ</text>
        
        <g transform="translate(400, 250)">
            <rect x="-12.5" y="-60" width="25" height="120" fill="#D4AF37" rx="4"/>
            <rect x="-60" y="-12.5" width="120" height="25" fill="#D4AF37" rx="4"/>
            <path d="M 12.5 -60 L 40 -60 L 40 -35 L 12.5 -35 Z" fill="#D4AF37"/>
            <path d="M 60 -12.5 L 60 12.5 L 35 12.5 L 35 -12.5 Z" fill="#D4AF37"/>
            <path d="M -12.5 60 L -40 60 L -40 35 L -12.5 35 Z" fill="#D4AF37"/>
            <path d="M -60 12.5 L -60 -12.5 L -35 -12.5 L -35 12.5 Z" fill="#D4AF37"/>
        </g>
        
        <text x="400" y="420" font-size="36" fill="#4A154B" text-anchor="middle" font-weight="bold" letter-spacing="2">FORENSIC ASTROLOGICAL</text>
        <text x="400" y="470" font-size="36" fill="#4A154B" text-anchor="middle" font-weight="bold" letter-spacing="2">DOSSIER</text>
        
        <line x1="300" y1="500" x2="500" y2="500" stroke="#D4AF37" stroke-width="2"/>
        <text x="400" y="540" font-size="14" fill="#666666" text-anchor="middle" letter-spacing="1">KARMIC ARCHITECTURE &amp; STRATEGIC INTELLIGENCE</text>
        
        <text x="400" y="650" font-size="18" fill="#222222" text-anchor="middle" font-weight="bold">{native_name}</text>
        <text x="400" y="680" font-size="14" fill="#666666" text-anchor="middle">{birth_str}</text>
        
        <text x="400" y="1020" font-size="48" fill="#4A154B" text-anchor="middle" font-weight="bold">ॐ</text>
        <text x="400" y="1050" font-size="10" fill="#999999" text-anchor="middle">Generated via Pure Mathematical Precision</text>
    </svg>
    """

def generate_rasi_chart_svg(planet_positions, asc_sign, chart_title="Rasi Chart (D-1)"):
    width = 400; height = 420
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    h_coords = {
        1: (180, 60), 2: (90, 30), 3: (30, 90), 4: (60, 180),
        5: (30, 270), 6: (90, 330), 7: (180, 300), 8: (270, 330),
        9: (330, 270), 10: (300, 180), 11: (330, 90), 12: (270, 30)
    }
    
    house_planets = {i: [] for i in range(1, 13)}
    for p_name, data in planet_positions.items():
        p_sign = data.get("sign", "Aries")
        p_sign_idx = ZODIAC_SIGNS.index(p_sign)
        h_num = ((p_sign_idx - asc_idx + 12) % 12) + 1
        abbr = p_name.split("/")[0].strip()[:2]
        if data.get("retro"):
            abbr += "®"
        house_planets[h_num].append(abbr)
        
    svg = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; font-family: sans-serif;">',
        f'<text x="200" y="20" font-size="14" font-weight="bold" fill="#4A154B" text-anchor="middle">{chart_title}</text>',
        '<g transform="translate(20, 40)">',
        '<rect x="0" y="0" width="360" height="360" fill="#ffffff" stroke="#4A154B" stroke-width="3" rx="4"/>',
        '<polygon points="180,0 360,180 180,360 0,180" fill="none" stroke="#4A154B" stroke-width="2"/>',
        '<line x1="0" y1="0" x2="360" y2="360" stroke="#4A154B" stroke-width="1.5"/>',
        '<line x1="360" y1="0" x2="0" y2="360" stroke="#4A154B" stroke-width="1.5"/>'
    ]
    
    for h_num, (x, y) in h_coords.items():
        sign_num = ((asc_idx + (h_num - 1)) % 12) + 1
        svg.append(f'<text x="{x}" y="{y-15}" font-size="9" fill="#999999" text-anchor="middle">{sign_num}</text>')
        if house_planets[h_num]:
            svg.append(f'<text x="{x}" y="{y+5}" font-size="11" font-weight="bold" fill="#4A154B" text-anchor="middle">{", ".join(house_planets[h_num])}</text>')
            
    svg.append('</g></svg>')
    return "\n".join(svg)

def generate_sav_heatmap_svg(sav_dict):
    width = 600; height = 280; margin_top = 30; margin_bottom = 45
    chart_height = height - margin_top - margin_bottom; y_scale = chart_height / 50 
    baseline_y = height - margin_bottom - (28 * y_scale)
    
    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; font-family: sans-serif;">',
        '<rect width="100%" height="100%" fill="#faf9f6" rx="6" />',
        f'<line x1="30" y1="{baseline_y:.2f}" x2="{width-30}" y2="{baseline_y:.2f}" stroke="#4A154B" stroke-width="1.5" stroke-dasharray="4,4" />',
        f'<text x="{width-35}" y="{baseline_y-6:.2f}" font-size="9" fill="#4A154B" text-anchor="end" font-weight="bold">Karmic Baseline (28)</text>'
    ]
    
    for i in range(1, 13):
        score = sav_dict.get(i, 0)
        bar_height = max(0, min(score, 50)) * y_scale
        x = 35 + ((i - 1) * 44); y = height - margin_bottom - bar_height
        color = "#2e7d32" if score >= 28 else "#c62828"
        svg_parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="34" height="{bar_height:.2f}" fill="{color}" rx="3" ry="3" />')
        svg_parts.append(f'<text x="{x + 17:.2f}" y="{y - 5:.2f}" font-size="10" font-weight="bold" fill="#333333" text-anchor="middle">{score}</text>')
        svg_parts.append(f'<text x="{x + 17:.2f}" y="{height - margin_bottom + 18}" font-size="10" fill="#555555" text-anchor="middle">H{i}</text>')
        
    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

# ==========================================
# PDF GENERATION ENGINE
# ==========================================
def generate_pdf_weasyprint(html_content, pdf_path):
    try:
        HTML(string=html_content).write_pdf(pdf_path)
        return True
    except Exception as e:
        print(f"WEASYPRINT ERROR: {e}", flush=True)
        return False

# ==========================================
# LLM ORCHESTRATION & PIPELINE
# ==========================================
def send_message(chat_id, text):
    try: requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except: pass

def send_document(chat_id, file_path):
    try:
        with open(file_path, 'rb') as f:
            requests.post(f"{TELEGRAM_API_URL}/sendDocument", data={'chat_id': chat_id}, files={'document': f}, timeout=30)
    except: pass

def call_groq_agent(system_prompt, user_prompt, models_list, json_mode=False):
    groq_key = os.environ.get("GROQ_API_KEY")
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    if isinstance(models_list, str): models_list = [models_list]
        
    payload_base = {"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.3}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
    
    for model_name in models_list:
        payload = payload_base.copy()
        payload["model"] = model_name
        for attempt in range(2):
            try:
                res = requests.post(groq_url, headers=headers, json=payload, timeout=180)
                if res.status_code == 200:
                    return res.json()['choices'][0]['message']['content']
                elif res.status_code == 429:
                    print(f"RATE LIMIT (429) on {model_name}. Backing off 20s (Attempt {attempt+1}/2)...", flush=True)
                    time.sleep(20)
                    continue
                else: break
            except Exception as e:
                break
    return json.dumps({"error": "API_ERROR"}) if json_mode else "[ERROR: ALL MODELS FAILED]"

def llm_output_firewall(text):
    clean_text = re.sub(r'\b(potentially|possibly|assuming)\b', '', text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def process_background_task(chat_id, session_data):
    MASTER_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "groq/compound"]
    send_message(chat_id, "⏳ Initiating Agentic Swarm Pipeline (Premium Dossier Mode)...")

    base_cognitive_rules = """You are an Elite Vedic Astrological Strategic Advisor.
    [ABSOLUTE LAWS]
    1. NAMING STANDARD: Use clean bilingual headers formatted strictly as 'English Name / Hindi Name' (e.g., 'Moon / Chandra').
    2. MARKDOWN TABLES: Format your structural outputs strictly using clear Markdown Tables with columns (e.g. Area | Risk Vector | Strategic Asset | Synthesis) where applicable. DO NOT USE RAW ARRAYS or BRACKETS for data.
    3. JSON OUTPUT ONLY: Output a valid JSON object matching the requested schema without markdown wrappers."""

    base_user_msg = f"[INPUT DATA]\n{session_data['logic_breakdown']}\n[PLANETARY ARRAY]\nAscendant: {session_data['asc_sign']}\n{session_data['planet_summary']}"

    swarm_chapters = {
        "temporal_narrative": base_cognitive_rules + "\nOutput JSON with key 'temporal_narrative' containing keys: 'psychological_baseline', 'historical_trajectory', 'expected_survival'. Values MUST be single formatted strings.",
        "structural_analysis": base_cognitive_rules + "\nOutput JSON with key 'structural_analysis' containing keys: 'wealth_and_career', 'relationships_and_property', 'vitality_and_subconscious'. Format each as a string with bullet points (- **Risk Vector**, - **Strategic Asset**, - **Synthesis**).",
        "navamsha_relational_audit": base_cognitive_rules + "\nOutput JSON with key 'navamsha_relational_audit' containing a single key 'marital_karma_and_friction'. The value MUST be a single string formatted as a Markdown table with columns: | Planet (D-9 Sign) | Karmic Friction / Strategic Asset | Interpretation |. Do NOT output JSON arrays.",
        "dashamsha_career_vector": base_cognitive_rules + "\nOutput JSON with key 'dashamsha_career_vector' containing a single key 'professional_apex_potential'. The value MUST be a single string formatted as a Markdown table with columns: | Planet (D-10 Sign) | Strategic Asset / Karmic Friction | Professional Impact |. Do NOT output JSON arrays.",
        "pratyantardasha_24_month_plan": base_cognitive_rules + "\nOutput JSON with key 'pratyantardasha_24_month_plan' containing a single key 'high_probability_events'. The value MUST be a single string formatted as a Markdown table with columns: | Timeframe | Event | Strategic Focus / Karmic Friction |. Do NOT output JSON arrays.",
        "ayurvedic_audit": base_cognitive_rules + "\nNOTE: The English/Hindi naming rule applies only to Planets and Zodiac Signs, NOT to Ayurvedic Doshas. \nOutput JSON with key 'ayurvedic_audit' containing a single string diagnosing the Dosha and lifestyle shifts.",
        "remediation_protocol": base_cognitive_rules + "\nAnalyze the [LAL KITAB RULES] in the input data. Output JSON with key 'remediation_protocol' containing keys: 'suppressing_afflictions', 'amplifying_assets'. Values MUST be a single formatted string using '\\n' for line breaks and markdown bullets ('- '), NOT a JSON array or list.",
        "lal_kitab_architecture": base_cognitive_rules + "\nOutput JSON with key 'lal_kitab_architecture' containing keys: 'environmental_hazards_to_avoid', 'home_structure_remedies'. Values MUST be single formatted strings using markdown bullets."
    }

    eng_data = {}
    for chapter_key, system_prompt in swarm_chapters.items():
        send_message(chat_id, f"🧠 Analyzing: {chapter_key.replace('_', ' ').title()}...")
        res = call_groq_agent(system_prompt, base_user_msg, MASTER_MODELS)
        res = res.strip()
        if res.startswith("```json"): res = res[7:]
        if res.startswith("```"): res = res[3:]
        if res.endswith("```"): res = res[:-3]
        try:
            eng_data.update(json.loads(res.strip()))
        except Exception as e:
            pass
        time.sleep(15)

    if not eng_data:
        send_message(chat_id, "⚠️ Swarm Agents failed to generate data.")
        return

    def recursive_firewall(data):
        if isinstance(data, dict): return {k: recursive_firewall(v) for k, v in data.items()}
        elif isinstance(data, list): return [recursive_firewall(v) for v in data]
        elif isinstance(data, str): return llm_output_firewall(data)
        return data

    eng_data = recursive_firewall(eng_data)
    
    def md_to_html(text):
        if isinstance(text, list):
            text = "\n".join([f"- {item}" if isinstance(item, str) else f"- {json.dumps(item)}" for item in text])
        elif isinstance(text, dict):
            text = json.dumps(text, indent=2)
        return markdown2.markdown(str(text), extras=["fenced-code-blocks", "tables"])

    heatmap_svg, rasi_svg = "", ""
    sav_match = re.search(r'\[FULL SARVASHTAKAVARGA \(SAV\) MATRIX\]:\s*(\{.*?\})', session_data['logic_breakdown'])
    if sav_match:
        try: heatmap_svg = generate_sav_heatmap_svg({int(k): v for k, v in json.loads(sav_match.group(1)).items()})
        except: pass

    rasi_svg = generate_rasi_chart_svg(session_data['planet_data'], session_data['asc_sign'])
    birth_str = session_data.get("birth_str", "")
    cover_svg = generate_cover_page_svg(native_name="Confidential Dossier", birth_str=birth_str)

    html_body = f"""
    <div class="cover-page" style="text-align: center; margin: 0; padding: 0;">
        {cover_svg}
    </div>
    
    <div class="content">
        <div style="text-align: center; margin-bottom: 30px; margin-top: 20px;">
            <h1 style="font-size: 24pt; color: #4A154B; margin-bottom: 5px;">STRUCTURAL INTEGRITY & CHARTS</h1>
            <hr style="width: 40%; border: 1px solid #4A154B; margin-top: 15px;">
        </div>
        
        <div class="chart-container">
            <div class="chart-box" style="margin-bottom: 40px;">
                {rasi_svg}
            </div>
        </div>

        <div class="sav-box">
            <h3 style="text-align: center; margin-top: 0; color: #4A154B;">Sarvashtakavarga (SAV) Karmic Heatmap</h3>
            {heatmap_svg}
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">I. TEMPORAL-PSYCHOLOGICAL NARRATIVE</h2>
        <h3 class="sub-title">The Psychological Baseline</h3>
        {md_to_html(safe_get(eng_data, ["temporal_narrative", "psychological_baseline"]))}
        <h3 class="sub-title">Expected Survival & Forecast</h3>
        {md_to_html(safe_get(eng_data, ["temporal_narrative", "expected_survival"]))}
        
        <div class="page-break"></div>
        <h2 class="section-title">II. STRUCTURAL INTEGRITY ANALYSIS</h2>
        <h3 class="sub-title">Wealth & Career Pillar</h3>
        {md_to_html(safe_get(eng_data, ["structural_analysis", "wealth_and_career"]))}
        <h3 class="sub-title">Vitality & Subconscious Pillar</h3>
        {md_to_html(safe_get(eng_data, ["structural_analysis", "vitality_and_subconscious"]))}
        
        <div class="page-break"></div>
        <h2 class="section-title">III. DIVISIONAL CHART (VARGA) DEEP DIVE</h2>
        <div class="varga-block">
            <h3 class="sub-title">Marital Karma & Friction (D-9)</h3>
            {md_to_html(safe_get(eng_data, ["navamsha_relational_audit", "marital_karma_and_friction"]))}
        </div>
        <div class="varga-block">
            <h3 class="sub-title">Professional Apex Potential (D-10)</h3>
            {md_to_html(safe_get(eng_data, ["dashamsha_career_vector", "professional_apex_potential"]))}
        </div>
        
        <div class="page-break"></div>
        <h2 class="section-title">IV. FORECAST & NEUROLOGICAL AUDIT</h2>
        <div class="narrative-block">
            <h3 class="sub-title">24-Month Tactical Forecast</h3>
            {md_to_html(safe_get(eng_data, ["pratyantardasha_24_month_plan", "high_probability_events"]))}
        </div>
        <div class="narrative-block">
            <h3 class="sub-title">Ayurvedic Audit</h3>
            {md_to_html(safe_get(eng_data, ["ayurvedic_audit"]))}
        </div>
        
        <div class="page-break"></div>
        <h2 class="section-title">V. REMEDIATION PROTOCOL</h2>
        <div class="remedy-box affliction">
            <h3 style="margin-top: 0; color: #c62828;">Suppressing Afflictions</h3>
            {md_to_html(safe_get(eng_data, ["remediation_protocol", "suppressing_afflictions"]))}
        </div>
        <div class="remedy-box asset">
            <h3 style="margin-top: 0; color: #2e7d32;">Amplifying Assets</h3>
            {md_to_html(safe_get(eng_data, ["remediation_protocol", "amplifying_assets"]))}
        </div>

        <h3 class="sub-title" style="margin-top: 30px;">Lal Kitab Environmental Protocols (Vastu)</h3>
        <div style="margin-bottom: 15px;">
            <strong>Hazards to Avoid:</strong>
            {md_to_html(safe_get(eng_data, ["lal_kitab_architecture", "environmental_hazards_to_avoid"]))}
        </div>
        <div>
            <strong>Structural Remedies:</strong>
            {md_to_html(safe_get(eng_data, ["lal_kitab_architecture", "home_structure_remedies"]))}
        </div>
    </div>
    """

    css = """
    @page { size: letter; margin: 2.54cm; }
    body { font-family: 'Noto Sans', 'Helvetica', sans-serif; font-size: 10pt; line-height: 1.6; color: #222; margin: 0; padding: 0; }
    .cover-page { height: 100vh; }
    .page-break { page-break-before: always; }
    h1 { color: #4A154B; font-size: 24pt; border-bottom: 2px solid #D4AF37; padding-bottom: 10px; }
    h2.section-title { color: #4A154B; font-size: 16pt; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #e0e0e0; padding-bottom: 5px; margin-bottom: 20px; }
    h3.sub-title { color: #4A154B; font-size: 12pt; font-style: italic; margin-top: 20px; margin-bottom: 10px; }
    strong { color: #111; font-weight: 600; }
    ul { padding-left: 20px; margin-bottom: 15px; }
    li { margin-bottom: 6px; }
    /* PREMIUM TABLE STYLING */
    table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 10pt; }
    th { background-color: #4A154B; color: #ffffff; padding: 10px; text-align: left; border: 1px solid #4A154B; }
    td { padding: 10px; border: 1px solid #e0e0e0; vertical-align: top; }
    tr:nth-child(even) { background-color: #faf9f6; }
    .chart-container { text-align: center; }
    .chart-box { width: 350px; margin: 0 auto; }
    .sav-box { margin: 20px 0; border: 1px solid #D4AF37; padding: 20px; border-radius: 8px; background: #fdfbf7; }
    .varga-block, .narrative-block { margin-bottom: 30px; }
    .remedy-box { padding: 15px 20px; margin-bottom: 15px; border-radius: 0 8px 8px 0; }
    .remedy-box.affliction { background: #fdf8f8; border-left: 4px solid #c62828; }
    .remedy-box.asset { background: #f4fbf4; border-left: 4px solid #2e7d32; }
    """
    full_html = f"<html><head><style>{css}</style></head><body>{html_body}</body></html>"
    
    send_message(chat_id, "⏳ Compiling Premium Overhauled PDF...")
    pdf_path = f"/tmp/Astrological_Dossier_{int(time.time())}.pdf"
    
    if generate_pdf_weasyprint(full_html, pdf_path) and os.path.exists(pdf_path):
        send_document(chat_id, pdf_path)
        send_message(chat_id, "📄 **Strategic Dossier PDF attached above!** ⬆️")
    else:
        send_message(chat_id, "⚠️ PDF generation failed.")

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
            send_message(chat_id, "Welcome to the Premium Dossier Bot. Send birth details: `DD-MM-YYYY HH:MM City`")
            return jsonify(status="success"), 200
                
        match = re.search(r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{2,4})\s+(\d{1,2}):(\d{1,2})\s+(.+)', user_text)
        if match:
            day, month, year, hour, minute, city_input = match.groups()
            year = int(year) + (1900 if int(year) > 25 else 2000) if int(year) < 100 else int(year)
            send_message(chat_id, "⏳ Calculating geometric and astronomical arrays...")
            try:
                res = requests.get(f"[https://nominatim.openstreetmap.org/search?q=](https://nominatim.openstreetmap.org/search?q=){city_input}&format=json&limit=1", headers={'User-Agent': 'Bot/1.0'}, timeout=5).json()
                lat, lon = float(res[0]['lat']), float(res[0]['lon'])
                city_clean = res[0].get('display_name', city_input).split(',')[0]
            except: 
                lat, lon = 30.7333, 76.7794
                city_clean = city_input
                    
            asc_sign, planets, logic_breakdown, age = calculate_sidereal_chart(int(day), int(month), int(year), int(hour), int(minute), lat, lon)
            session = {
                "state": "ready", 
                "asc_sign": asc_sign, 
                "planet_data": planets,
                "planet_summary": "\n".join([f"- {p}: {d['hindi_sign']} | Dignity: {d['dignity']}" for p, d in planets.items()]),
                "logic_breakdown": logic_breakdown,
                "birth_str": f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean} (Age: {age})"
            }
            save_session(chat_id, session)
            threading.Thread(target=process_background_task, args=(chat_id, session)).start()
            return jsonify(status="success"), 200
            
    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        
    return jsonify(status="success"), 200

init_db()

if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
