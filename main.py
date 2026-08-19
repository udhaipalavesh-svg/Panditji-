# ==========================================
# THE CELESTIAL STRATEGY DOSSIER (FINAL BUILD)
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
# ASTROLOGY CONSTANTS & MATH TABLES
# ==========================================
ZODIAC_SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
HINDI_SIGNS = {"Aries": "Aries / Mesha", "Taurus": "Taurus / Vrishabha", "Gemini": "Gemini / Mithuna", "Cancer": "Cancer / Karka", "Leo": "Leo / Simha", "Virgo": "Virgo / Kanya", "Libra": "Libra / Tula", "Scorpio": "Scorpio / Vrishchika", "Sagittarius": "Sagittarius / Dhanu", "Capricorn": "Capricorn / Makara", "Aquarius": "Aquarius / Kumbha", "Pisces": "Pisces / Meena"}
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
DASHA_LORDS = [("Ketu / Ketu", 7), ("Venus / Shukra", 20), ("Sun / Surya", 6), ("Moon / Chandra", 10), ("Mars / Mangal", 7), ("Rahu / Rahu", 18), ("Jupiter / Guru", 16), ("Saturn / Shani", 19), ("Mercury / Budh", 17)]
EXALTATION = {"Sun / Surya": "Aries", "Moon / Chandra": "Taurus", "Mars / Mangal": "Capricorn", "Mercury / Budh": "Virgo", "Jupiter / Guru": "Cancer", "Venus / Shukra": "Pisces", "Saturn / Shani": "Libra", "Rahu / Rahu": "Taurus", "Ketu / Ketu": "Scorpio"}
DEBILITATION = {"Sun / Surya": "Libra", "Moon / Chandra": "Scorpio", "Mars / Mangal": "Cancer", "Mercury / Budh": "Pisces", "Jupiter / Guru": "Capricorn", "Venus / Shukra": "Virgo", "Saturn / Shani": "Aries", "Rahu / Rahu": "Scorpio", "Ketu / Ketu": "Taurus"}
OWN_SIGNS = {"Sun / Surya": ["Leo"], "Moon / Chandra": ["Cancer"], "Mars / Mangal": ["Aries", "Scorpio"], "Mercury / Budh": ["Gemini", "Virgo"], "Jupiter / Guru": ["Sagittarius", "Pisces"], "Venus / Shukra": ["Taurus", "Libra"], "Saturn / Shani": ["Capricorn", "Aquarius"]}
COMBUSTION_ORB = {"Moon / Chandra": 12, "Mars / Mangal": 17, "Mercury / Budh": 14, "Jupiter / Guru": 11, "Venus / Shukra": 10, "Saturn / Shani": 15}

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
# DATABASE MANAGER (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (chat_id INTEGER PRIMARY KEY, session_data TEXT)''')
    conn.commit(); conn.close()

def save_session(chat_id, data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO sessions (chat_id, session_data) VALUES (?, ?)", (chat_id, json.dumps(data)))
    conn.commit(); conn.close()

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
    conn.commit(); conn.close()

def safe_get(data, keys, default="*Data Unavailable*"):
    if not isinstance(data, dict): return default
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current: current = current[key]
        else: return default
    return current if current else default

# ==========================================
# MATHEMATICAL ENGINE
# ==========================================
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

def calculate_full_sav(houses_dict):
    planets_for_sav = ["Sun / Surya", "Moon / Chandra", "Mars / Mangal", "Mercury / Budh", "Jupiter / Guru", "Venus / Shukra", "Saturn / Shani"]
    sav_scores = {}
    for house_num in range(1, 13):
        h_total = 0
        for p in planets_for_sav:
            p_h = next((h for h, d in houses_dict.items() if p in d["occupants"]), None)
            if p_h and p in BAV_TABLES:
                idx = (((house_num - p_h) % 12)) * 8
                h_total += sum(BAV_TABLES[p][idx : idx + 8])
        sav_scores[house_num] = h_total
    return sav_scores

def get_nakshatra_info(lon):
    nak_idx = int(lon / (360.0 / 27.0)) % 27
    return nak_idx, NAKSHATRAS[nak_idx]

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

def fmt_jd_to_mon_year(jd):
    y, m, d = swe.revjul(jd)[:3]
    return f"{m:02d}/{y}"

def calculate_vimshottari_timeline(moon_lon, birth_dt):
    nak_span = 360.0 / 27.0
    nak_idx, _ = get_nakshatra_info(moon_lon)
    lord_idx = (nak_idx // 3) % 9
    rem = moon_lon % nak_span
    
    fraction_remaining = 1.0 - (rem / nak_span)
    birth_jd = swe.julday(birth_dt.year, birth_dt.month, birth_dt.day)
    now_jd = swe.julday(datetime.now().year, datetime.now().month, datetime.now().day)
    
    curr_m_idx = lord_idx
    curr_m_start_jd = birth_jd
    curr_m_years = DASHA_LORDS[curr_m_idx][1] * fraction_remaining
    
    while True:
        curr_m_end_jd = curr_m_start_jd + (curr_m_years * 365.25)
        if curr_m_end_jd > now_jd:
            m_lord = DASHA_LORDS[curr_m_idx][0]
            a_idx = curr_m_idx
            a_years = (DASHA_LORDS[a_idx][1] * DASHA_LORDS[curr_m_idx][1]) / 120.0
            if curr_m_idx == lord_idx: a_years *= fraction_remaining
            a_start_jd = curr_m_start_jd
            
            while True:
                a_end_jd = a_start_jd + (a_years * 365.25)
                if a_end_jd > now_jd:
                    a_lord = DASHA_LORDS[a_idx][0]
                    next_a_idx = (a_idx + 1) % 9
                    next_a_start_jd = a_end_jd
                    next_a_end_jd = next_a_start_jd + ((DASHA_LORDS[next_a_idx][1] * DASHA_LORDS[curr_m_idx][1]) / 120.0 * 365.25)
                    return f"Current AD: {m_lord}-{a_lord} [{fmt_jd_to_mon_year(a_start_jd)} to {fmt_jd_to_mon_year(a_end_jd)}] | Next AD: {m_lord}-{DASHA_LORDS[next_a_idx][0]} [{fmt_jd_to_mon_year(next_a_start_jd)} to {fmt_jd_to_mon_year(next_a_end_jd)}]"
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

def detect_yogas(houses_dict, planets_dict, sign_lords):
    yogas = []
    moon_house = next((h for h, d in houses_dict.items() if "Moon / Chandra" in d["occupants"]), None)
    jup_house = next((h for h, d in houses_dict.items() if "Jupiter / Guru" in d["occupants"]), None)
    
    if moon_house and jup_house and abs(jup_house - moon_house) in [0, 3, 6, 9]:
        yogas.append("Gaja Kesari Yoga (Jupiter in Kendra from Moon): Traditionally indicates intellectual capacity, reputation, and sustained leadership.")
    
    kendra_houses = [1, 4, 7, 10]; trikona_houses = [1, 5, 9]
    kendra_lords = [sign_lords.get(houses_dict[h]["sign"], "") for h in kendra_houses]
    trikona_lords = [sign_lords.get(houses_dict[h]["sign"], "") for h in trikona_houses]
    
    for h_num, data in houses_dict.items():
        occupants = data["occupants"]
        for kl in kendra_lords:
            for tl in trikona_lords:
                if kl and tl and kl != tl and kl in occupants and tl in occupants:
                    yogas.append(f"Raja Yoga ({kl} conjunct {tl} in House {h_num}): Traditionally linked to elevation in status, capability, and strategic authority.")
    return list(dict.fromkeys(yogas))

def get_lal_kitab_remedy(houses_dict, planets_dict):
    remedies = []
    for p_name, p_data in planets_dict.items():
        if p_data.get("combust") and f"{p_name}_Combust" in LAL_KITAB_DICT: remedies.append(f"{p_name}: {LAL_KITAB_DICT[f'{p_name}_Combust']}")
        if p_data.get("dignity", "").startswith("Debilitated") and f"{p_name}_Debilitated" in LAL_KITAB_DICT: remedies.append(f"{p_name}: {LAL_KITAB_DICT[f'{p_name}_Debilitated']}")
    for h_num, data in houses_dict.items():
        for p_name in [p for p in data["occupants"] if p in ["Saturn / Shani", "Mars / Mangal", "Rahu / Rahu", "Ketu / Ketu", "Sun / Surya"]]:
            if f"{p_name}_{h_num}" in LAL_KITAB_DICT: remedies.append(f"{p_name} in House {h_num}: {LAL_KITAB_DICT[f'{p_name}_{h_num}']}")
    return list(dict.fromkeys(remedies))

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
        _, nak_name = get_nakshatra_info(lon_val)
        positions[name] = {
            "sign": sign_name, "hindi_sign": HINDI_SIGNS[sign_name], "lon": lon_val % 360.0, 
            "nak": nak_name, "dignity": get_planet_dignity(name, sign_name),
            "combust": (abs(lon_val - sun_lon) < COMBUSTION_ORB.get(name, 0)) if name in COMBUSTION_ORB else False
        }
        
    try: _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags); asc_lon = ascmc[0] % 360.0
    except: asc_lon = 0.0
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]
    
    # House & Logic Compilation
    sign_lords = {"Aries": "Mars / Mangal", "Taurus": "Venus / Shukra", "Gemini": "Mercury / Budh", "Cancer": "Moon / Chandra", "Leo": "Sun / Surya", "Virgo": "Mercury / Budh", "Libra": "Venus / Shukra", "Scorpio": "Mars / Mangal", "Sagittarius": "Jupiter / Guru", "Capricorn": "Saturn / Shani", "Aquarius": "Saturn / Shani", "Pisces": "Jupiter / Guru"}
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    houses = {i+1: {"sign": ZODIAC_SIGNS[(asc_idx + i) % 12], "occupants": [], "aspected_by": []} for i in range(12)}
    for p_name, p_data in positions.items():
        for h_num, h_data in houses.items():
            if h_data["sign"] == p_data["sign"]: h_data["occupants"].append(p_name); break
    for p_name, p_data in positions.items():
        occ_h = next((h for h, d in houses.items() if p_name in d["occupants"]), None)
        if occ_h:
            for ah in get_aspects(p_name, occ_h): houses[ah]["aspected_by"].append(p_name)

    fact_sheet = "[PLANETARY MATRIX]\n"
    for h, data in houses.items():
        fact_sheet += f"- H{h} ({data['sign']}): Occ: {', '.join(data['occupants']) or 'Empty'}. Asp: {', '.join(data['aspected_by']) or 'None'}.\n"
    
    logic_summary = fact_sheet
    logic_summary += f"\n[TIMELINE]: {calculate_vimshottari_timeline(positions['Moon / Chandra']['lon'], dt_ist)}\n[TRANSITS]: {calculate_transit_timings()}"
    yogas = detect_yogas(houses, positions, sign_lords)
    logic_summary += "\n[YOGAS]: " + (" | ".join(yogas) if yogas else "None.")
    logic_summary += f"\n[VARGAS]: {json.dumps(calculate_vargas(positions))}\n[SAV]: {json.dumps(calculate_full_sav(houses))}"
    logic_summary += f"\n[LAL KITAB RULES]: " + " | ".join(get_lal_kitab_remedy(houses, positions))
    
    return asc_sign, positions, logic_summary, (datetime.now() - dt_ist).days // 365

# ==========================================
# VISUAL RENDERERS (SVG)
# ==========================================
def generate_cover_page_svg(native_name="Confidential Dossier", birth_str=""):
    return f"""
    <svg viewBox="0 0 800 1130" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: 100vh; font-family: 'Helvetica', sans-serif;">
        <rect width="800" height="1130" fill="#101827" />
        <rect x="30" y="30" width="740" height="1070" fill="none" stroke="#B68A3A" stroke-width="1" />
        <circle cx="400" cy="565" r="300" fill="none" stroke="#B68A3A" stroke-width="0.5" stroke-dasharray="4,8" opacity="0.4"/>
        <circle cx="400" cy="565" r="200" fill="none" stroke="#B68A3A" stroke-width="0.5" stroke-dasharray="2,4" opacity="0.3"/>
        
        <text x="400" y="380" font-size="28" fill="#F5F0E6" text-anchor="middle" font-weight="300" letter-spacing="4">THE CELESTIAL STRATEGY</text>
        <text x="400" y="440" font-size="48" fill="#B68A3A" text-anchor="middle" font-weight="bold" letter-spacing="6">DOSSIER</text>
        
        <line x1="300" y1="480" x2="500" y2="480" stroke="#B68A3A" stroke-width="1"/>
        <text x="400" y="520" font-size="12" fill="#71866B" text-anchor="middle" letter-spacing="2">NATAL ARCHITECTURE • LIFE THEMES • TIMING MAP</text>
        
        <text x="400" y="800" font-size="12" fill="#F5F0E6" text-anchor="middle" letter-spacing="1">PREPARED FOR</text>
        <text x="400" y="830" font-size="18" fill="#B68A3A" text-anchor="middle" font-weight="bold" letter-spacing="2">{native_name}</text>
        <text x="400" y="860" font-size="12" fill="#71866B" text-anchor="middle">{birth_str}</text>
        
        <text x="400" y="1050" font-size="10" fill="#71866B" text-anchor="middle">Generated via Pure Mathematical Precision</text>
    </svg>
    """

def generate_rasi_chart_svg(planet_positions, asc_sign, chart_title="Natal Architecture (D-1)"):
    width = 400; height = 400
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    
    # House Centers
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
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; font-family: sans-serif;">',
        '<rect x="0" y="0" width="400" height="400" fill="#F5F0E6" stroke="#101827" stroke-width="2"/>',
        '<polygon points="200,0 400,200 200,400 0,200" fill="none" stroke="#101827" stroke-width="1.5"/>',
        '<line x1="0" y1="0" x2="400" y2="400" stroke="#101827" stroke-width="1"/>',
        '<line x1="400" y1="0" x2="0" y2="400" stroke="#101827" stroke-width="1"/>',
        '<line x1="0" y1="200" x2="400" y2="200" stroke="#101827" stroke-width="1"/>',
        '<line x1="200" y1="0" x2="200" y2="400" stroke="#101827" stroke-width="1"/>'
    ]
    
    for h_num, (x, y) in h_coords.items():
        # Correct North Indian representation: Draw Zodiac Sign number
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

def generate_strength_bars(score=80, label=""):
    width = int((score/100) * 150)
    return f"""
    <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size:9pt; color:#71866B; text-transform:uppercase; letter-spacing:1px; width: 100px;">{label}</span>
        <div style="width:150px; background:#e0e0e0; height:6px; border-radius:3px;">
            <div style="width:{width}px; background:#B68A3A; height:6px; border-radius:3px;"></div>
        </div>
    </div>
    """

# ==========================================
# PDF COMPILER
# ==========================================
def generate_pdf_weasyprint(html_content, pdf_path):
    try: HTML(string=html_content).write_pdf(pdf_path); return True
    except Exception as e: print(f"PDF ERROR: {e}", flush=True); return False

# ==========================================
# LLM ORCHESTRATION
# ==========================================
def send_message(chat_id, text):
    try: requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except: pass

def send_document(chat_id, file_path):
    try:
        with open(file_path, 'rb') as f:
            requests.post(f"{TELEGRAM_API_URL}/sendDocument", data={'chat_id': chat_id}, files={'document': f}, timeout=30)
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

def llm_output_firewall(text):
    return re.sub(r'\s+', ' ', text).strip()

def process_background_task(chat_id, session_data):
    MASTER_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "groq/compound"]
    send_message(chat_id, "⏳ Compiling The Celestial Strategy Dossier (Premium Format)...")

    # Strict Premium Directives
    base_cognitive_rules = """You are an Elite Executive Astrological Advisor.
    [ABSOLUTE LAWS]
    1. MEDICAL DISCLAIMER: Never predict lifespan, cure conditions, or make clinical diagnoses. Frame observations as "traditionally associated with" or "may indicate".
    2. NARRATIVE DECOUPLING: DO NOT list or suggest any remedies (silver, copper, mantras) in diagnostic sections. Remedies are strictly quarantined to the final chapter.
    3. TONE: Dark, precise, premium, analytical. Output MUST be valid JSON matching the schema."""

    base_user_msg = f"[PLANETARY ARRAY]\nAscendant: {session_data['asc_sign']}\n{session_data['planet_summary']}\n[DATA LOGIC]\n{session_data['logic_breakdown']}"

    swarm_chapters = {
        "executive_summary": base_cognitive_rules + "\nOutput JSON with key 'executive' containing 'core_identity' (string summarizing cognitive/leadership style) and 'headline_themes' (Markdown table: Theme | Strategic Posture for Career, Finance, Relationships).",
        "chart_decoder": base_cognitive_rules + "\nReview the [YOGAS] and planetary data. Output JSON with key 'decoder' containing 'key_signatures' (Markdown table: Planetary Signature or Yoga | Plain-Language Meaning | Watchpoint).",
        "varga_deep_dive": base_cognitive_rules + "\nAnalyze the [VARGAS] D-9 and D-10 data. Output JSON with key 'varga_analysis' containing 'relational_and_career_impact' (Markdown table: Varga & Planet | Strategic Asset / Karmic Friction | Professional or Relational Impact).",
        "life_domains": base_cognitive_rules + "\nOutput JSON with key 'domains' containing an object with 6 keys: career, wealth, relationships, health, learning, home. Each key contains an object with: 'asset' (string), 'friction' (string), 'prompt' (a reflective question).",
        "tactical_forecast": base_cognitive_rules + "\nAnalyze the [TIMELINE] and [TRANSITS]. Output JSON with key 'forecast' containing '24_month_timeline' (Markdown table: Timeframe | Event | Strategic Focus).",
        "wellbeing_protocol": base_cognitive_rules + "\nOutput JSON with key 'wellbeing' containing an object with 4 keys: daily_rhythm, food_energy, mental_reset, movement. Each a single string. DO NOT mention medical cures.",
        "remediation_planner": base_cognitive_rules + "\nAnalyze [LAL KITAB RULES]. Output JSON with key 'remedies' containing a single Markdown table (Ritual/Remedy | Required For | Reflective Intent)."
    }

    eng_data = {}
    for chapter_key, system_prompt in swarm_chapters.items():
        send_message(chat_id, f"🧠 Synthesizing: {chapter_key.replace('_', ' ').title()}...")
        res = call_groq_agent(system_prompt, base_user_msg, MASTER_MODELS).strip()
        if res.startswith("```json"): res = res[7:]
        if res.startswith("```"): res = res[3:]
        if res.endswith("```"): res = res[:-3]
        try: eng_data.update(json.loads(res.strip()))
        except: pass
        time.sleep(15)

    def md_to_html(text):
        if isinstance(text, dict): return ""
        return markdown2.markdown(str(text), extras=["fenced-code-blocks", "tables"])

    cover_svg = generate_cover_page_svg(native_name="Confidential Profile", birth_str=session_data.get("birth_str", ""))
    rasi_svg = generate_rasi_chart_svg(session_data['planet_data'], session_data['asc_sign'])
    
    sav_match = re.search(r'\[SAV\]:\s*(\{.*?\})', session_data['logic_breakdown'])
    heatmap_svg = generate_sav_heatmap_svg({int(k): v for k, v in json.loads(sav_match.group(1)).items()}) if sav_match else ""

    sb_career = generate_strength_bars(85, "Career")
    sb_finance = generate_strength_bars(70, "Wealth")
    sb_rel = generate_strength_bars(60, "Relationships")
    sb_energy = generate_strength_bars(75, "Vitality")

    html_body = f"""
    <div class="cover-page">{cover_svg}</div>
    
    <div class="content">
        <h2 class="section-title">01 — Executive Snapshot</h2>
        <div class="grid-2col" style="margin-bottom: 40px;">
            <div>
                <h3 class="sub-title">Core Identity</h3>
                <p>{safe_get(eng_data, ['executive', 'core_identity'], '')}</p>
            </div>
            <div style="background:#F5F0E6; padding:20px; border-radius:4px; border:1px solid #B68A3A;">
                <h3 class="sub-title" style="margin-top:0;">Life Theme Capacities</h3>
                {sb_career}{sb_finance}{sb_rel}{sb_energy}
                <p style="font-size:7pt; color:#71866B; margin-top:10px;">*Interpretive indicators, not measured scores.</p>
            </div>
        </div>
        {md_to_html(safe_get(eng_data, ['executive', 'headline_themes']))}

        <div class="page-break"></div>
        <h2 class="section-title">02 — Natal Architecture</h2>
        <div class="grid-2col">
            <div class="chart-box" style="margin-top: 10px;">{rasi_svg}</div>
            <div>
                <h3 class="sub-title" style="margin-top:0;">Chart Decoder & Key Yogas</h3>
                {md_to_html(safe_get(eng_data, ['decoder', 'key_signatures']))}
            </div>
        </div>
        
        <h3 class="sub-title" style="margin-top: 30px;">Sarvashtakavarga (SAV) Karmic Heatmap</h3>
        <div class="sav-box">{heatmap_svg}</div>

        <div class="page-break"></div>
        <h2 class="section-title">03 — Divisional Intelligence (Vargas)</h2>
        <p style="font-size:9pt; color:#71866B; border:1px solid #B68A3A; padding:10px; background:#F5F0E6;">Deep dive into D-9 Navamsha (Subconscious & Relational) and D-10 Dashamsha (Career Apex & Execution).</p>
        {md_to_html(safe_get(eng_data, ['varga_analysis', 'relational_and_career_impact']))}

        <div class="page-break"></div>
        <h2 class="section-title">04 — Life Domain Dashboard</h2>
        <div class="grid-2col">
            <div class="domain-card">
                <h4 style="color:#B68A3A; margin-top:0;">💼 Career & Leadership</h4>
                <p><strong>Strong Pattern:</strong> {safe_get(eng_data, ['domains', 'career', 'asset'], '')}</p>
                <p><strong>Development Edge:</strong> {safe_get(eng_data, ['domains', 'career', 'friction'], '')}</p>
                <p class="reflection"><em>Prompt: {safe_get(eng_data, ['domains', 'career', 'prompt'], '')}</em></p>
            </div>
            <div class="domain-card">
                <h4 style="color:#B68A3A; margin-top:0;">🏛️ Wealth & Resources</h4>
                <p><strong>Strong Pattern:</strong> {safe_get(eng_data, ['domains', 'wealth', 'asset'], '')}</p>
                <p><strong>Development Edge:</strong> {safe_get(eng_data, ['domains', 'wealth', 'friction'], '')}</p>
                <p class="reflection"><em>Prompt: {safe_get(eng_data, ['domains', 'wealth', 'prompt'], '')}</em></p>
            </div>
            <div class="domain-card">
                <h4 style="color:#B68A3A; margin-top:0;">🤝 Relationships</h4>
                <p><strong>Strong Pattern:</strong> {safe_get(eng_data, ['domains', 'relationships', 'asset'], '')}</p>
                <p><strong>Development Edge:</strong> {safe_get(eng_data, ['domains', 'relationships', 'friction'], '')}</p>
                <p class="reflection"><em>Prompt: {safe_get(eng_data, ['domains', 'relationships', 'prompt'], '')}</em></p>
            </div>
            <div class="domain-card">
                <h4 style="color:#B68A3A; margin-top:0;">⚡ Health & Vitality</h4>
                <p><strong>Strong Pattern:</strong> {safe_get(eng_data, ['domains', 'health', 'asset'], '')}</p>
                <p><strong>Development Edge:</strong> {safe_get(eng_data, ['domains', 'health', 'friction'], '')}</p>
                <p class="reflection"><em>Prompt: {safe_get(eng_data, ['domains', 'health', 'prompt'], '')}</em></p>
            </div>
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">05 — Tactical Forecast & Wellbeing</h2>
        <h3 class="sub-title">24-Month Timing Map</h3>
        {md_to_html(safe_get(eng_data, ['forecast', '24_month_timeline']))}
        
        <h3 class="sub-title" style="margin-top: 30px;">Wellbeing Protocol</h3>
        <p style="font-size:8pt; color:#71866B;">*For personal reflection only. Not medical advice.</p>
        <div class="grid-2col" style="margin-top:10px;">
            <div class="domain-card" style="border-top-color:#71866B;">
                <h4 style="color:#101827; margin-top:0;">Daily Rhythm</h4>
                <p>{safe_get(eng_data, ['wellbeing', 'daily_rhythm'], '')}</p>
            </div>
            <div class="domain-card" style="border-top-color:#71866B;">
                <h4 style="color:#101827; margin-top:0;">Food & Energy</h4>
                <p>{safe_get(eng_data, ['wellbeing', 'food_energy'], '')}</p>
            </div>
            <div class="domain-card" style="border-top-color:#71866B;">
                <h4 style="color:#101827; margin-top:0;">Mental Reset</h4>
                <p>{safe_get(eng_data, ['wellbeing', 'mental_reset'], '')}</p>
            </div>
            <div class="domain-card" style="border-top-color:#71866B;">
                <h4 style="color:#101827; margin-top:0;">Movement</h4>
                <p>{safe_get(eng_data, ['wellbeing', 'movement'], '')}</p>
            </div>
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">06 — Traditional Practices & Planner</h2>
        <p style="font-size:9pt; color:#71866B; margin-bottom: 20px;">Optional cultural and spiritual practices derived from Lal Kitab algorithms. Use for intention, reflection, and routine grounding.</p>
        {md_to_html(safe_get(eng_data, ['remedies']))}
    </div>
    """

    css = """
    @page { size: letter; margin: 2.54cm; }
    body { font-family: 'Helvetica', sans-serif; font-size: 10pt; line-height: 1.6; color: #101827; margin: 0; padding: 0; }
    .cover-page { height: 100vh; }
    .page-break { page-break-before: always; }
    h1, h2.section-title { color: #101827; font-size: 18pt; text-transform: uppercase; letter-spacing: 2px; border-bottom: 1px solid #B68A3A; padding-bottom: 5px; margin-bottom: 25px; }
    h3.sub-title { color: #101827; font-size: 12pt; text-transform: uppercase; letter-spacing: 1px; margin-top: 15px; margin-bottom: 10px; }
    .grid-2col { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 20px; }
    .grid-2col > div { width: 48%; }
    .domain-card { background: #F5F0E6; padding: 15px; border-top: 3px solid #B68A3A; margin-bottom: 20px; width: 45%; }
    .reflection { background: #101827; color: #F5F0E6; padding: 10px; font-size: 9pt; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 9.5pt; }
    th { background-color: #101827; color: #B68A3A; padding: 12px; text-align: left; text-transform: uppercase; letter-spacing: 1px; }
    td { padding: 12px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }
    tr:nth-child(even) { background-color: #F5F0E6; }
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
                    
            asc_sign, planets, logic_breakdown, age = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
            session = {
                "state": "ready", "asc_sign": asc_sign, "planet_data": planets,
                "planet_summary": "\n".join([f"- {p}: {d['hindi_sign']} | Dignity: {d['dignity']}" for p, d in planets.items()]),
                "logic_breakdown": logic_breakdown,
                "birth_str": f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean} (Age: {age})"
            }
            save_session(chat_id, session)
            threading.Thread(target=process_background_task, args=(chat_id, session)).start()
            
    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        
    return jsonify(status="success"), 200

init_db()

if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
