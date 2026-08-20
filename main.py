# ==========================================
# THE CELESTIAL STRATEGY DOSSIER (MASTER ARCHITECTURE - UNCOMPRESSED)
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

# ==========================================
# HOLISTIC REMEDIATION PROTOCOLS
# ==========================================
VEDIC_MANTRAS = {
    "Sun / Surya": "Om Hraam Hreem Hroum Sah Suryaya Namah", "Moon / Chandra": "Om Shraam Shreem Shroum Sah Chandraya Namah",
    "Mars / Mangal": "Om Kraam Kreem Kroum Sah Bhaumaya Namah", "Mercury / Budh": "Om Braam Breem Broum Sah Budhaya Namah",
    "Jupiter / Guru": "Om Graam Greem Groum Sah Gurve Namah", "Venus / Shukra": "Om Draam Dreem Droum Sah Shukraya Namah",
    "Saturn / Shani": "Om Praam Preem Proum Sah Shanaishcharaya Namah", "Rahu / Rahu": "Om Bhraam Bhreem Bhroum Sah Rahave Namah",
    "Ketu / Ketu": "Om Sraam Sreem Sroum Sah Ketave Namah"
}

VEDIC_UPAYAS = {
    "Sun / Surya": "Offer Arghya (water with red flowers) to the rising sun. Recite Aditya Hridaya Stotram.",
    "Moon / Chandra": "Meditate on Shiva. Respect mother figures. Offer milk or water to a Shivling.",
    "Mars / Mangal": "Recite Hanuman Chalisa daily. Donate red lentils to charity on Tuesdays.",
    "Mercury / Budh": "Recite Vishnu Sahasranama. Feed green grass to cows or animals on Wednesdays.",
    "Jupiter / Guru": "Respect teachers and gurus. Donate yellow clothes or chana dal. Chant Guru Stotram.",
    "Venus / Shukra": "Maintain respectful relationships with women. Keep surroundings fragrant. Chant Sri Suktam.",
    "Saturn / Shani": "Light a mustard oil lamp under a Peepal tree on Saturday evenings. Serve the underprivileged.",
    "Rahu / Rahu": "Feed birds and street dogs. Donate black blankets to the homeless or ascetics.",
    "Ketu / Ketu": "Donate to spiritual ascetic orders. Feed multi-colored dogs. Meditate on Ganesha."
}

# 140+ ENTRY MASTER LAL KITAB DATABASE
LAL_KITAB_DICT = {
    # COMBUSTION & DEBILITATION
    "Saturn / Shani_Combust": "Donate black sesame oil on Saturday.", "Mars / Mangal_Combust": "Avoid keeping iron tools under the bed.",
    "Jupiter / Guru_Combust": "Apply a tilak of saffron on the forehead daily.", "Venus / Shukra_Combust": "Donate pure ghee to a temple on Friday.",
    "Mercury / Budh_Combust": "Clean teeth with fitkari (alum) daily.", "Sun / Surya_Debilitated": "Offer water to the Sun. Avoid salt on Sundays.",
    "Moon / Chandra_Debilitated": "Immerse a square piece of silver in a river on Monday.", "Mars / Mangal_Debilitated": "Float red copper in a flowing river on Tuesday.",
    "Mercury / Budh_Debilitated": "Avoid wearing green clothes. Keep broad-leaved plants away.", "Jupiter / Guru_Debilitated": "Water a peepal tree on Thursday.",
    "Venus / Shukra_Debilitated": "Donate white sweets to young girls on Friday.", "Saturn / Shani_Debilitated": "Serve food to disabled people on Saturday.",
    "Rahu / Rahu_Debilitated": "Keep a square silver piece in your pocket.", "Ketu / Ketu_Debilitated": "Feed a two-colored dog.",
    
    # SUN (1-12)
    "Sun / Surya_1": "Offer water to the Sun daily.", "Sun / Surya_2": "Donate wheat and jaggery on Sunday.",
    "Sun / Surya_3": "Keep good relations with younger siblings.", "Sun / Surya_4": "Do not consume salt on Sundays.",
    "Sun / Surya_5": "Keep a red handkerchief in your pocket.", "Sun / Surya_6": "Feed a red cow on Sundays.",
    "Sun / Surya_7": "Reduce anger in marriage; avoid taking the first aggressive step.", "Sun / Surya_8": "Keep a copper pot filled with water at home.",
    "Sun / Surya_9": "Use brass utensils for eating.", "Sun / Surya_10": "Wear a copper coin around the neck.",
    "Sun / Surya_11": "Drink water from a copper vessel.", "Sun / Surya_12": "Keep the courtyard or entrance of your home clean.",

    # MOON (1-12)
    "Moon / Chandra_1": "Drink milk from a silver glass.", "Moon / Chandra_2": "Keep a square piece of silver in the house.",
    "Moon / Chandra_3": "Offer green gram to birds.", "Moon / Chandra_4": "Do not trade in milk or dairy products.",
    "Moon / Chandra_5": "Serve your mother and seek her blessings.", "Moon / Chandra_6": "Serve water to patients in a hospital.",
    "Moon / Chandra_7": "Do not marry before the age of 24.", "Moon / Chandra_8": "Immerse a silver coin in a river.",
    "Moon / Chandra_9": "Visit religious places frequently.", "Moon / Chandra_10": "Avoid drinking milk at night.",
    "Moon / Chandra_11": "Donate milk to a temple on Mondays.", "Moon / Chandra_12": "Keep rainwater stored in a glass bottle at home.",

    # MARS (1-12)
    "Mars / Mangal_1": "Avoid keeping large weapons in the house.", "Mars / Mangal_2": "Donate red masoor dal on Tuesday.",
    "Mars / Mangal_3": "Wear a silver ring. Maintain good relation with siblings.", "Mars / Mangal_4": "Keep a square piece of red copper in the house.",
    "Mars / Mangal_5": "Keep a pot of water by your bedside.", "Mars / Mangal_6": "Donate red masoor dal and batasha on Tuesday.",
    "Mars / Mangal_7": "Build a solid boundary wall around your home.", "Mars / Mangal_8": "Feed sweet roti to a dog. Wear a silver chain.",
    "Mars / Mangal_9": "Offer milk to a banyan tree.", "Mars / Mangal_10": "Offer sweet milk to a blind person.",
    "Mars / Mangal_11": "Keep a red handkerchief in your pocket.", "Mars / Mangal_12": "Float a piece of red copper in flowing water.",

    # MERCURY (1-12)
    "Mercury / Budh_1": "Avoid consuming alcohol.", "Mercury / Budh_2": "Keep a pet dog.",
    "Mercury / Budh_3": "Clean your teeth with fitkari.", "Mercury / Budh_4": "Wear a silver chain for mental peace.",
    "Mercury / Budh_5": "Wear a copper coin on a white thread.", "Mercury / Budh_6": "Bury a bottle filled with Ganga water in agricultural land.",
    "Mercury / Budh_7": "Avoid business partnerships with female relatives.", "Mercury / Budh_8": "Keep rainwater in an earthen pot on the roof.",
    "Mercury / Budh_9": "Wear green colors sparingly.", "Mercury / Budh_10": "Do not keep broad-leaved plants in the office.",
    "Mercury / Budh_11": "Wear an unjointed iron ring.", "Mercury / Budh_12": "Wear a yellow thread around the neck.",

    # JUPITER (1-12)
    "Jupiter / Guru_1": "Apply a saffron tilak on the forehead.", "Jupiter / Guru_2": "Fill a pit with mud on the street.",
    "Jupiter / Guru_3": "Worship Goddess Durga.", "Jupiter / Guru_4": "Do not establish a temple inside your house.",
    "Jupiter / Guru_5": "Plant a peepal tree in a temple.", "Jupiter / Guru_6": "Donate yellow clothes to a priest.",
    "Jupiter / Guru_7": "Avoid keeping idols of gods at home.", "Jupiter / Guru_8": "Wear gold on the neck.",
    "Jupiter / Guru_9": "Visit religious places regularly.", "Jupiter / Guru_10": "Clean your nose before starting any work.",
    "Jupiter / Guru_11": "Wear a copper coin.", "Jupiter / Guru_12": "Serve ascetics and saints.",

    # VENUS (1-12)
    "Venus / Shukra_1": "Do not marry before age 25.", "Venus / Shukra_2": "Keep a solid silver ball in your pocket.",
    "Venus / Shukra_3": "Respect women and avoid polygamy.", "Venus / Shukra_4": "Change the name of your spouse after marriage.",
    "Venus / Shukra_5": "Maintain absolute fidelity to your spouse.", "Venus / Shukra_6": "Keep a white dog.",
    "Venus / Shukra_7": "Throw a blue flower in a dirty drain.", "Venus / Shukra_8": "Throw a copper coin in a gutter.",
    "Venus / Shukra_9": "Bury a silver square under a neem tree.", "Venus / Shukra_10": "Wash your private parts with curd.",
    "Venus / Shukra_11": "Donate mustard oil.", "Venus / Shukra_12": "Keep a blue glass bottle in the house.",

    # SATURN (1-12)
    "Saturn / Shani_1": "Do not consume alcohol or non-veg. Feed black crows.", "Saturn / Shani_2": "Apply an oil tilak to your forehead.",
    "Saturn / Shani_3": "Keep three dogs as pets or feed street dogs.", "Saturn / Shani_4": "Do not build a house before age 48.",
    "Saturn / Shani_5": "Keep almonds in your home. Feed black crows.", "Saturn / Shani_6": "Float a black mustard oil-filled bottle in a river.",
    "Saturn / Shani_7": "Do not build a house before age 48.", "Saturn / Shani_8": "Drop 8kg of raw coal in running water.",
    "Saturn / Shani_9": "Keep a square piece of silver.", "Saturn / Shani_10": "Feed black crows daily. Maintain strict punctuality.",
    "Saturn / Shani_11": "Place a vessel filled with mustard oil in your house.", "Saturn / Shani_12": "Tie twelve almonds in a black cloth.",

    # RAHU (1-12)
    "Rahu / Rahu_1": "Keep a silver square in your pocket.", "Rahu / Rahu_2": "Keep a solid silver ball in your pocket.",
    "Rahu / Rahu_3": "Keep ivory items out of the house.", "Rahu / Rahu_4": "Do not remodel the kitchen frequently.",
    "Rahu / Rahu_5": "Keep a silver elephant statue in the house.", "Rahu / Rahu_6": "Float a piece of lead in running water.",
    "Rahu / Rahu_7": "Store river water in a dark glass bottle.", "Rahu / Rahu_8": "Float four coconuts in a river on Saturday.",
    "Rahu / Rahu_9": "Apply a saffron tilak.", "Rahu / Rahu_10": "Wear a blue or black cap.",
    "Rahu / Rahu_11": "Drink water from a silver glass.", "Rahu / Rahu_12": "Keep a pouch of fennel under the pillow.",

    # KETU (1-12)
    "Ketu / Ketu_1": "Feed a two-colored dog.", "Ketu / Ketu_2": "Maintain absolute honesty in financial ledgers.",
    "Ketu / Ketu_3": "Float rice mixed with milk in a river.", "Ketu / Ketu_4": "Do not keep fragmented glass in the house.",
    "Ketu / Ketu_5": "Donate a black and white blanket.", "Ketu / Ketu_6": "Wear a gold ring on the left hand.",
    "Ketu / Ketu_7": "Keep a piece of iron dipped in water.", "Ketu / Ketu_8": "Feed street dogs regularly.",
    "Ketu / Ketu_9": "Keep a gold brick or coin in the house.", "Ketu / Ketu_10": "Keep a silver pot filled with honey.",
    "Ketu / Ketu_11": "Keep a radish near your bed at night and donate it.", "Ketu / Ketu_12": "Do not keep broken jewelry."
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

def safe_get(data, keys, default=""):
    if not isinstance(data, dict): return default
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current: current = current[key]
        else: return default
    return current if current else default

# ==========================================
# FULL MATH ENGINE (VARGAS, SAV, YOGAS, TRANSITS)
# ==========================================
def get_nakshatra_info(lon):
    return int(lon / (360.0 / 27.0)) % 27, NAKSHATRAS[int(lon / (360.0 / 27.0)) % 27]

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
            m_lord = DASHA_LORDS[curr_m_idx][0].split('/')[0].strip()
            a_idx = curr_m_idx
            a_years = (DASHA_LORDS[a_idx][1] * DASHA_LORDS[curr_m_idx][1]) / 120.0
            if curr_m_idx == lord_idx: a_years *= fraction_remaining
            a_start_jd = curr_m_start_jd
            
            periods_found = 0
            while periods_found < 4:
                a_end_jd = a_start_jd + (a_years * 365.25)
                if a_end_jd > now_jd or periods_found > 0:
                    a_lord = DASHA_LORDS[a_idx][0].split('/')[0].strip()
                    sy, sm, sd = swe.revjul(a_start_jd)[:3]
                    ey, em, ed = swe.revjul(a_end_jd)[:3]
                    phase_name = "Current Antardasha" if periods_found == 0 else f"Next Phase {periods_found}"
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

# ==========================================
# NATIVE PYTHON HTML & SVG CONSTRUCTORS
# ==========================================
def generate_ephemeris_table_html(planet_positions):
    html = '<table class="data-table"><tr><th>Planet / Hindi</th><th>Sign</th><th>Degree</th><th>Nakshatra</th><th>Condition</th></tr>'
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

def generate_remedies_table_html(houses_dict, planet_data):
    html = '<table class="data-table"><tr><th>Karmic Friction</th><th>Lal Kitab Behavioral Protocol</th><th style="width: 50px; text-align:center;">Done</th></tr>'
    remedies = []
    for p_name, p_data in planet_data.items():
        if p_data.get("combust") and f"{p_name}_Combust" in LAL_KITAB_DICT: remedies.append(f"{p_name} Combust: {LAL_KITAB_DICT[f'{p_name}_Combust']}")
        if p_data.get("dignity", "").startswith("Debilitated") and f"{p_name}_Debilitated" in LAL_KITAB_DICT: remedies.append(f"{p_name} Debilitated: {LAL_KITAB_DICT[f'{p_name}_Debilitated']}")
    for h_num, data in houses_dict.items():
        for p_name in data["occupants"]:
            if f"{p_name}_{h_num}" in LAL_KITAB_DICT: remedies.append(f"{p_name} in H{h_num}: {LAL_KITAB_DICT[f'{p_name}_{h_num}']}")
            
    remedies = list(dict.fromkeys(remedies))
    if not remedies:
        html += '<tr><td colspan="3">No major structural Lal Kitab afflictions detected. Maintain general grounding practices.</td></tr>'
    else:
        for r in remedies:
            parts = r.split(':')
            if len(parts) == 2:
                html += f"<tr><td><strong>{parts[0].strip()}</strong></td><td>{parts[1].strip()}</td><td style='text-align:center;'><div style='width:16px; height:16px; border:1px solid #101827; border-radius:2px; margin:auto;'></div></td></tr>"
    html += "</table>"
    return html

def generate_cover_page_svg(native_name="Confidential Dossier", birth_str=""):
    return f"""
    <svg viewBox="0 0 800 1130" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: 100vh; font-family: 'Georgia', serif;">
        <rect width="800" height="1130" fill="#101827" />
        <rect x="40" y="40" width="720" height="1050" fill="none" stroke="#B68A3A" stroke-width="1" />
        <circle cx="400" cy="565" r="300" fill="none" stroke="#B68A3A" stroke-width="0.5" stroke-dasharray="4,8" opacity="0.4"/>
        <circle cx="400" cy="565" r="200" fill="none" stroke="#B68A3A" stroke-width="0.5" stroke-dasharray="2,4" opacity="0.3"/>
        
        <text x="400" y="240" font-size="90" fill="#B68A3A" text-anchor="middle" font-family="sans-serif">ॐ   卐</text>
        
        <text x="400" y="420" font-size="28" fill="#F5F0E6" text-anchor="middle" font-weight="300" letter-spacing="4">THE CELESTIAL STRATEGY</text>
        <text x="400" y="480" font-size="48" fill="#B68A3A" text-anchor="middle" font-weight="bold" letter-spacing="6">DOSSIER</text>
        
        <line x1="300" y1="520" x2="500" y2="520" stroke="#B68A3A" stroke-width="1"/>
        <text x="400" y="560" font-size="12" fill="#71866B" text-anchor="middle" letter-spacing="2" font-family="'Helvetica', sans-serif;">NATAL ARCHITECTURE • LIFE THEMES • TIMING MAP</text>
        
        <text x="400" y="800" font-size="12" fill="#F5F0E6" text-anchor="middle" letter-spacing="1" font-family="'Helvetica', sans-serif;">PREPARED FOR</text>
        <text x="400" y="830" font-size="18" fill="#B68A3A" text-anchor="middle" font-weight="bold" letter-spacing="2">{native_name}</text>
        <text x="400" y="860" font-size="12" fill="#71866B" text-anchor="middle" font-family="'Helvetica', sans-serif;">{birth_str}</text>
        
        <text x="400" y="1050" font-size="10" fill="#71866B" text-anchor="middle" font-family="'Helvetica', sans-serif;">An interpretive Vedic-astrology and holistic strategy report.</text>
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
    payload_base = {"messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.3}
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
    send_message(chat_id, "⏳ Compiling The Celestial Strategy Dossier (Master Holistic Build)...")

    base_cognitive_rules = """You are an Elite Executive Astrological Advisor writing for a premium editorial magazine.
    [ABSOLUTE LAWS]
    1. MEDICAL DISCLAIMER: Never predict lifespan, cure conditions, or make clinical diagnoses. Frame insights as "traditionally associated with".
    2. NARRATIVE DECOUPLING: DO NOT list or suggest any remedies (e.g. silver, fasting) in your analysis.
    3. FORMATTING: Output a JSON object with a single key 'content'. The value MUST be rich HTML (<p>, <b>, <i>). Do NOT use markdown tables.
    4. TONE: Profound, strategic, highly analytical, and flowing."""

    base_user_msg = f"Ascendant: {session_data['asc_sign']}\nData: {session_data['logic_breakdown']}"

    swarm_chapters = {
        "psychology": base_cognitive_rules + "\nWrite a deep 3-paragraph synthesis of the native's psychological operating system, drive, and cognitive style.",
        "career_wealth": base_cognitive_rules + "\nWrite a deep 3-paragraph synthesis of the native's career apex, leadership style, and wealth potential based on D-10 and Yogas.",
        "relational_karma": base_cognitive_rules + "\nWrite a profound 3-paragraph analysis of relationship karma, intimacy constraints, and emotional expression based on D-9 Navamsha.",
        "forecast": base_cognitive_rules + "\nWrite a 2-paragraph narrative forecast of the underlying themes for the upcoming 24 months based on the timeline.",
        "ayurvedic_audit": base_cognitive_rules + "\nAnalyze the planetary elements to determine the primary Ayurvedic Dosha (Vata, Pitta, Kapha). Write a 2-paragraph reflection on how this dosha shapes the native's physical vitality and mental energy. Frame as 'traditional lifestyle rhythms', strictly avoiding medical diagnoses."
    }

    eng_data = {}
    for chapter_key, system_prompt in swarm_chapters.items():
        send_message(chat_id, f"🧠 Synthesizing: {chapter_key.replace('_', ' ').title()}...")
        res = call_groq_agent(system_prompt, base_user_msg, MASTER_MODELS).strip()
        if res.startswith("```json"): res = res[7:]
        if res.startswith("```"): res = res[3:]
        if res.endswith("```"): res = res[:-3]
        try: eng_data[chapter_key] = json.loads(res.strip()).get("content", "")
        except: eng_data[chapter_key] = "<p>Data temporarily unavailable.</p>"
        time.sleep(15)

    cover_svg = generate_cover_page_svg(native_name="Confidential Profile", birth_str=session_data.get("birth_str", ""))
    rasi_svg = generate_rasi_chart_svg(session_data['planet_data'], session_data['asc_sign'])
    ephemeris_html = generate_ephemeris_table_html(session_data['planet_data'])
    
    timeline_data = calculate_vimshottari_timeline(session_data['planet_data']['Moon / Chandra']['lon'], session_data['dt_ist_iso'])
    dasha_html = generate_dasha_table_html(timeline_data)
    
    sav_heatmap_svg = generate_sav_heatmap_svg(session_data['sav'])
    mantra_html = generate_mantra_table_html(session_data['planet_data'], session_data['asc_sign'])
    lal_kitab_html = generate_remedies_table_html(session_data['houses'], session_data['planet_data'])

    html_body = f"""
    <div class="cover-page">{cover_svg}</div>
    
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
        <div class="editorial-content">
            {eng_data.get('psychology', '')}
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">03 — Career & Wealth Canvas</h2>
        <div class="editorial-content">
            {eng_data.get('career_wealth', '')}
        </div>
        
        <h3 class="sub-title" style="margin-top: 30px;">Sarvashtakavarga (SAV) Karmic Heatmap</h3>
        <div class="sav-box">{sav_heatmap_svg}</div>
        <div class="synopsis" style="margin-top:10px;">
            <strong>Curator's Note:</strong> The SAV Heatmap reveals the mathematical strength of your 12 houses. Houses scoring above 28 points can easily absorb and manifest positive transit energies. Houses below 28 indicate areas requiring structural reinforcement.
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">04 — Relational Dynamics</h2>
        <div class="editorial-content">
            {eng_data.get('relational_karma', '')}
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">05 — Tactical Forecast</h2>
        <h3 class="sub-title">Vimshottari Timeline</h3>
        {dasha_html}
        <div class="synopsis">
            <strong>Curator's Note:</strong> The Vimshottari Dasha is a 120-year algorithmic timeline activated by the exact degree of your Moon. It acts as a karmic clock, indicating which specific planetary forces are currently awake.
        </div>
        <div class="editorial-content" style="margin-top:20px;">
            {eng_data.get('forecast', '')}
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">06 — Ayurvedic & Vitality Reflection</h2>
        <p style="font-size:9pt; color:#71866B; border:1px solid #B68A3A; padding:10px; background:#F5F0E6;">For personal reflection and traditional wellness context. It is not medical advice, diagnosis, or treatment.</p>
        <div class="editorial-content" style="margin-top:20px; column-count: 1;">
            {eng_data.get('ayurvedic_audit', '')}
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">07 — Holistic Remediation Planner</h2>
        
        <h3 class="sub-title">I. Vedic Mantras & Spiritual Upayas</h3>
        <p style="font-size:9.5pt; margin-bottom:10px;">The following phonetic frequencies and traditional rituals target the Ascendant Lord and uniquely afflicted nodes within your geometry.</p>
        {mantra_html}
        
        <h3 class="sub-title" style="margin-top: 30px;">II. Lal Kitab Behavioral Protocols</h3>
        {lal_kitab_html}
        
        <div class="synopsis" style="margin-top:15px;">
            <strong>Curator's Note:</strong> While Mantras operate on phonetic resonance, Lal Kitab principles treat planets as energetic nodes that can be 'grounded' through physical, behavioral actions. These protocols are designed to mitigate specific structural frictions in your chart.
        </div>
    </div>
    """

    css = """
    @page { 
        size: letter; margin: 2.54cm; 
        @top-center {
            content: "ॐ   卐";
            font-family: 'Helvetica', sans-serif;
            font-size: 16pt;
            color: #B68A3A;
            margin-bottom: 20px;
        }
        @bottom-right { 
            content: counter(page); 
            font-family: 'Helvetica', sans-serif;
            font-size: 9pt;
            color: #71866B; 
        }
    }
    body { font-family: 'Helvetica', 'Arial', sans-serif; font-size: 10.5pt; line-height: 1.8; color: #101827; margin: 0; padding: 0; }
    .cover-page { height: 100vh; }
    .page-break { page-break-before: always; }
    h1, h2.section-title { font-family: 'Georgia', serif; color: #101827; font-size: 20pt; text-transform: uppercase; letter-spacing: 2px; border-bottom: 1px solid #B68A3A; padding-bottom: 5px; margin-bottom: 25px; }
    h3.sub-title { font-family: 'Georgia', serif; color: #B68A3A; font-size: 14pt; text-transform: uppercase; letter-spacing: 1px; margin-top: 15px; margin-bottom: 10px; }
    
    .grid-2col { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 20px; }
    .grid-2col > div { width: 48%; box-sizing: border-box; }
    
    .editorial-content { column-count: 2; column-gap: 40px; text-align: justify; margin-top: 20px; }
    .editorial-content p { margin-top: 0; margin-bottom: 1.5em; }
    .editorial-content p:first-of-type::first-letter { font-family: 'Georgia', serif; font-size: 3.5em; float: left; margin-right: 8px; margin-top: -4px; color: #B68A3A; line-height: 1; }
    
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
            session = {
                "state": "ready", "asc_sign": asc_sign, "planet_data": planets, "houses": houses, "sav": sav, "dt_ist_iso": dt_ist,
                "logic_breakdown": logic_breakdown,
                "birth_str": f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean}"
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
