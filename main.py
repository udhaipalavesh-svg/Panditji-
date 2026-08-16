import os
import requests
import re
import time
import concurrent.futures
import urllib.request
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
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

NAK_LORDS = ["Ketu", "Venus (Shukra)", "Sun (Surya)", "Moon (Chandra)", "Mars (Mangal)", "Rahu", "Jupiter (Guru)", "Saturn (Shani)", "Mercury (Budh)"]

# Nakshatra Pada Traits
NAK_PADA_TRAITS = {
    "Ashwini": ["Pioneering & Aggressive", "Stable & Patient", "Analytical & Critical", "Philosophical & Expansive"],
    "Bharani": ["Creative & Stubborn", "Emotional & Nurturing", "Intellectual & Ambitious", "Disciplined & Structured"],
    "Krittika": ["Authoritative & Sharp", "Sensitive & Protective", "Communicative & Restless", "Spiritual & Detached"],
    "Rohini": ["Materialistic & Magnetic", "Artistic & Emotional", "Intellectual & Curious", "Practical & Grounded"],
    "Mrigashira": ["Restless & Searching", "Stable & Accumulating", "Dual-minded & Anxious", "Philosophical & Questing"],
    "Ardra": ["Stormy & Disruptive", "Emotional & Sensitive", "Intellectual & Analytical", "Detached & Rebellious"],
    "Punarvasu": ["Expansive & Optimistic", "Nurturing & Reflective", "Intellectual & Restless", "Structured & Disciplined"],
    "Pushya": ["Protective & Nurturing", "Artistic & Stubborn", "Communicative & Clever", "Spiritual & Traditional"],
    "Ashlesha": ["Cunning & Intense", "Emotional & Possessive", "Intellectual & Strategic", "Detached & Mysterious"],
    "Magha": ["Proud & Traditional", "Stable & Accumulating", "Ambitious & Active", "Philosophical & Detached"],
    "Purva Phalguni": ["Lazy & Luxurious", "Creative & Emotional", "Intellectual & Playful", "Disciplined & Strict"],
    "Uttara Phalguni": ["Helpful & Proud", "Nurturing & Stubborn", "Communicative & Friendly", "Organized & Structured"],
    "Hasta": ["Resourceful & Clever", "Emotional & Sensitive", "Intellectual & Witty", "Practical & Disciplined"],
    "Chitra": ["Brilliant & Flashy", "Artistic & Stubborn", "Intellectual & Crafty", "Spiritual & Mystical"],
    "Swati": ["Restless & Independent", "Nurturing & Diplomatic", "Intellectual & Social", "Detached & Philosophical"],
    "Vishakha": ["Driven & Fiery", "Emotional & Jealous", "Intellectual & Goal-oriented", "Spiritual & Disciplined"],
    "Anuradha": ["Friendly & Disciplined", "Nurturing & Stubborn", "Communicative & Strategic", "Mystical & Detached"],
    "Jyeshtha": ["Authoritative & Protective", "Emotional & Secretive", "Intellectual & Cynical", "Philosophical & Detached"],
    "Mula": ["Investigative & Destructive", "Stable & Patient", "Intellectual & Philosophical", "Spiritual & Detached"],
    "Purva Ashadha": ["Proud & Invincible", "Creative & Emotional", "Intellectual & Persuasive", "Disciplined & Traditional"],
    "Uttara Ashadha": ["Victorious & Righteous", "Nurturing & Stubborn", "Communicative & Honest", "Disciplined & Structured"],
    "Shravana": ["Listening & Traditional", "Nurturing & Sentimental", "Intellectual & Inquisitive", "Spiritual & Detached"],
    "Dhanishta": ["Rhythmic & Wealthy", "Artistic & Stubborn", "Intellectual & Scientific", "Philosophical & Detached"],
    "Shatabhisha": ["Healing & Secretive", "Emotional & Sensitive", "Intellectual & Analytical", "Mystical & Detached"],
    "Purva Bhadrapada": ["Intense & Restless", "Emotional & Anxious", "Intellectual & Pessimistic", "Spiritual & Detached"],
    "Uttara Bhadrapada": ["Calm & Wise", "Nurturing & Patient", "Intellectual & Deep", "Mystical & Cosmic"],
    "Revati": ["Nurturing & Wealthy", "Artistic & Stubborn", "Intellectual & Friendly", "Spiritual & Detached"]
}

PLANET_NATURES = {
    "Sun (Surya)": "Authority, ego, vitality, soul, government",
    "Moon (Chandra)": "Mind, emotions, liquidity, mother, peace",
    "Mars (Mangal)": "Action, aggression, blood, real estate, courage",
    "Mercury (Budh)": "Intellect, communication, nervous system, commerce",
    "Jupiter (Guru)": "Wisdom, wealth expansion, children, liver, dharma",
    "Venus (Shukra)": "Pleasure, relationships, luxury, reproductive system, art",
    "Saturn (Shani)": "Structure, delay, restriction, bones, karma, labor",
    "Rahu": "Obsession, illusion, foreign things, sudden events, smoke",
    "Ketu": "Detachment, severance, past karma, hidden things, sharp objects"
}

HOUSE_DOMAINS = {
    1: "Self, physical body, vitality, identity",
    2: "Wealth, family, speech, food, liquid cash",
    3: "Effort, siblings, courage, communication, short trips",
    4: "Home, mother, real estate, vehicles, inner peace",
    5: "Intellect, children, romance, speculation, past karma",
    6: "Disease, debts, enemies, litigation, daily service",
    7: "Marriage, partnerships, business, public image",
    8: "Longevity, sudden trauma, transformation, inheritance, secrets",
    9: "Dharma, higher education, father, gurus, long travel",
    10: "Career, status, authority, karma in society",
    11: "Gains, network, elder siblings, fulfillment of desires",
    12: "Loss, expenses, isolation, foreign lands, Moksha, bed pleasures"
}

# ==========================================
# EXPANDED LAL KITAB ENGINE (Holistic Coverage)
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
    return unique_remedies[:5] # Expanded to 5 for holistic coverage

def get_nakshatra_lord(nak_idx): return NAK_LORDS[nak_idx % 9]

def get_nak_pada_trait(nak_name, pada):
    if nak_name in NAK_PADA_TRAITS and 1 <= pada <= 4: return NAK_PADA_TRAITS[nak_name][pada - 1]
    return "Unknown"

def calculate_divisional_sign(lon_val, division, sign_idx):
    deg_in_sign = lon_val % 30
    if division == 9:
        d_idx = int(deg_in_sign / (30/9))
        return (sign_idx * 9 + d_idx) % 12
    elif division == 7:
        d_idx = int(deg_in_sign / (30/7))
        start_offset = 0 if sign_idx % 2 == 0 else 6
        return (sign_idx + start_offset + d_idx) % 12
    elif division == 10:
        d_idx = int(deg_in_sign / 3)
        start_offset = 0 if sign_idx % 2 == 0 else 8
        return (sign_idx + start_offset + d_idx) % 12
    return sign_idx

def calculate_shadbala_lite(planet, sign, is_retro, is_combust, lon_val):
    score = 0.0
    if EXALTATION.get(planet) == sign: score += 1.0
    if DEBILITATION.get(planet) == sign: score -= 1.0
    if planet in OWN_SIGNS and sign in OWN_SIGNS[planet]: score += 0.5
    if is_retro:
        if planet in ["Saturn (Shani)", "Jupiter (Guru)", "Mars (Mangal)"]: score += 0.5
        else: score += 0.2
    if is_combust: score -= 1.5
    if score >= 1.0: return "High Strength (Shadbala: >1.0)"
    elif score <= -1.0: return "Severe Weakness (Shadbala: <-1.0)"
    elif score < 0: return "Low Strength (Shadbala: <0)"
    else: return "Moderate Strength (Shadbala: 0-1)"

def calculate_multi_transits(natal_moon_sign, natal_asc_sign):
    now_dt = datetime.now()
    swe.set_ephe_path(None); swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    dt_utc = now_dt - timedelta(hours=5, minutes=30)
    utc_decimal = dt_utc.hour + (dt_utc.minute / 60.0)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, utc_decimal)
    flags = swe.FLG_SWIEPH + swe.FLG_SPEED + swe.FLG_SIDEREAL
    
    t_sat = swe.calc_ut(jdut, swe.SATURN, flags); sat_lon = t_sat[0][0] if isinstance(t_sat[0], tuple) else t_sat[0]
    t_jup = swe.calc_ut(jdut, swe.JUPITER, flags); jup_lon = t_jup[0][0] if isinstance(t_jup[0], tuple) else t_jup[0]
    t_rahu = swe.calc_ut(jdut, swe.MEAN_NODE, flags); rahu_lon = t_rahu[0][0] if isinstance(t_rahu[0], tuple) else t_rahu[0]
    ketu_lon = (rahu_lon + 180.0) % 360.0
    
    transit_sat_sign = ZODIAC_SIGNS[int(sat_lon / 30) % 12]
    transit_jup_sign = ZODIAC_SIGNS[int(jup_lon / 30) % 12]
    transit_rahu_sign = ZODIAC_SIGNS[int(rahu_lon / 30) % 12]
    transit_ketu_sign = ZODIAC_SIGNS[int(ketu_lon / 30) % 12]
    
    moon_idx = ZODIAC_SIGNS.index(natal_moon_sign)
    asc_idx = ZODIAC_SIGNS.index(natal_asc_sign)
    
    def get_transit_impacts(transit_idx, natal_idx):
        diff = (transit_idx - natal_idx) % 12
        impacts = []
        if diff == 11: impacts.append("12th House (Loss/Expenses)")
        elif diff == 0: impacts.append("1st House (Identity/Health)")
        elif diff == 1: impacts.append("2nd House (Wealth/Family)")
        elif diff == 3: impacts.append("4th House (Home/Peace)")
        elif diff == 7: impacts.append("8th House (Trauma/Transformation)")
        elif diff == 9: impacts.append("10th House (Career/Status)")
        return diff, impacts

    sat_diff_moon, sat_impacts_moon = get_transit_impacts(ZODIAC_SIGNS.index(transit_sat_sign), moon_idx)
    sat_diff_asc, sat_impacts_asc = get_transit_impacts(ZODIAC_SIGNS.index(transit_sat_sign), asc_idx)
    sade_sati = "Inactive"
    if sat_diff_moon == 11: sade_sati = "Active - Phase 1 (Rising/12th from Moon)"
    elif sat_diff_moon == 0: sade_sati = "Active - Phase 2 (Peak/1st House Moon)"
    elif sat_diff_moon == 1: sade_sati = "Active - Phase 3 (Setting/2nd from Moon)"
    sat_report = f"Saturn in {HINDI_SIGNS[transit_sat_sign]} | Sade Sati: {sade_sati} | Over Moon: {', '.join(sat_impacts_moon) if sat_impacts_moon else 'Neutral'} | Over Lagna: {', '.join(sat_impacts_asc) if sat_impacts_asc else 'Neutral'}"

    jup_diff_moon, jup_impacts_moon = get_transit_impacts(ZODIAC_SIGNS.index(transit_jup_sign), moon_idx)
    jup_diff_asc, jup_impacts_asc = get_transit_impacts(ZODIAC_SIGNS.index(transit_jup_sign), asc_idx)
    jup_relief = "No direct relief aspect on Moon or Lagna."
    if jup_diff_moon in [0, 1, 4, 7, 8, 9]: jup_relief = f"Active relief/expansion over Moon's {', '.join(jup_impacts_moon)}."
    elif jup_diff_asc in [0, 1, 4, 7, 8, 9]: jup_relief = f"Active relief/expansion over Lagna's {', '.join(jup_impacts_asc)}."
    jup_report = f"Jupiter in {HINDI_SIGNS[transit_jup_sign]} | Relief Vector: {jup_relief}"

    rahu_diff_moon, rahu_impacts_moon = get_transit_impacts(ZODIAC_SIGNS.index(transit_rahu_sign), moon_idx)
    ketu_diff_moon, ketu_impacts_moon = get_transit_impacts(ZODIAC_SIGNS.index(transit_ketu_sign), moon_idx)
    node_report = f"Rahu in {HINDI_SIGNS[transit_rahu_sign]} (Disrupting {', '.join(rahu_impacts_moon) if rahu_impacts_moon else 'Neutral'}) | Ketu in {HINDI_SIGNS[transit_ketu_sign]} (Severing {', '.join(ketu_impacts_moon) if ketu_impacts_moon else 'Neutral'})"

    return f"{sat_report}\n{jup_report}\n{node_report}"

def detect_yogas(houses_dict, planets_dict, sign_lords):
    yogas = []
    def get_house(planet_name):
        for h_num, h_data in houses_dict.items():
            if planet_name in h_data["occupants"]: return h_num
        return None

    moon_house = get_house("Moon (Chandra)")
    jup_house = get_house("Jupiter (Guru)")
    sat_house = get_house("Saturn (Shani)")
    mars_house = get_house("Mars (Mangal)")
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
                yogas.append("Kemadruma Yoga (No valid planets in 2nd/12th from Moon, no Bhanga cancellation in Kendras): Severe psychological isolation, mental anguish, and financial struggles in early life.")

    if moon_house and jup_house:
        diff = abs(jup_house - moon_house)
        if diff in [0, 3, 6, 9]: 
            yogas.append("Gaja Kesari Yoga (Jupiter in Kendra from Moon): Grants high intelligence, fame, wealth, strong moral character.")

    if jup_house and rahu_house and jup_house == rahu_house:
        yogas.append("Guru Chandal Yoga (Jupiter conjunct Rahu): Distortion of wisdom, unethical associations.")
    if sat_house and mars_house and sat_house == mars_house:
        yogas.append("Shani-Mangal Dosha (Saturn conjunct Mars): Intense frustration, structural conflicts, high risk of accidents.")

    for p_name, p_data in planets_dict.items():
        if p_data.get("dignity", "").startswith("Debilitated"):
            deb_sign = p_data["sign"]
            exalt_lord = sign_lords.get(EXALTATION.get(p_name, ""))
            deb_lord = sign_lords.get(deb_sign, "")
            for lord in [exalt_lord, deb_lord]:
                if lord:
                    lord_house = get_house(lord)
                    if lord_house in [1, 4, 7, 10]:
                        yogas.append(f"Neecha Bhanga Raja Yoga for {p_name}: Debilitation canceled by {lord} in Kendra. The initial weakness transforms into immense late-life power and success.")
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

def generate_master_pdf(report_text, pdf_path, birth_details_str, name_str, planet_data, asc_sign, d9_planets, d9_asc_sign, hindi_font_name=None):
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

        h1_hindi_style = ParagraphStyle('H1_Hindi', parent=h1_style, fontName=hindi_font_name) if hindi_font_name else h1_style
        h2_hindi_style = ParagraphStyle('H2_Hindi', parent=h2_style, fontName=hindi_font_name) if hindi_font_name else h2_style
        h3_hindi_style = ParagraphStyle('H3_Hindi', parent=h3_style, fontName=hindi_font_name) if hindi_font_name else h3_style
        body_hindi_style = ParagraphStyle('Body_Hindi', parent=body_style, fontName=hindi_font_name) if hindi_font_name else body_style
        bullet_hindi_style = ParagraphStyle('Bullet_Hindi', parent=bullet_style, fontName=hindi_font_name) if hindi_font_name else bullet_style

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

        is_hindi_section = False
        for line in report_text.split('\n'):
            line = line.strip()
            if not line: continue
            
            safe_line = escape(line)
            safe_line = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', safe_line)
            safe_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_line)
            safe_line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', safe_line)
            
            if safe_line.startswith("# PART 2"):
                is_hindi_section = True
                
            cur_h1 = h1_hindi_style if is_hindi_section else h1_style
            cur_h2 = h2_hindi_style if is_hindi_section else h2_style
            cur_h3 = h3_hindi_style if is_hindi_section else h3_style
            cur_body = body_hindi_style if is_hindi_section else body_style
            cur_bullet = bullet_hindi_style if is_hindi_section else bullet_style
            
            if safe_line.startswith("# I.") or safe_line.startswith("# II.") or safe_line.startswith("# III.") or safe_line.startswith("# IV.") or safe_line.startswith("# PART 2"):
                if not (safe_line.startswith("# I.") or safe_line.startswith("# PART 2")): story.append(PageBreak())
                story.append(Paragraph(safe_line.replace("# ", ""), cur_h1))
                story.append(Spacer(1, 12))
            elif safe_line.startswith("# PART 3"): story.append(PageBreak()); story.append(Paragraph("COMPATIBILITY & SYNESTRY ANALYSIS", cur_h1)); story.append(Spacer(1, 12))
            elif safe_line.startswith("*Disclaimer:"):
                story.append(Spacer(1, 6)); story.append(Paragraph(safe_line, disclaimer_style)); story.append(Spacer(1, 10))
            elif safe_line.startswith("### "): story.append(Paragraph(safe_line.replace("### ", ""), cur_h3))
            elif re.match(r'^\d+\.\s+', safe_line):
                story.append(Paragraph(re.sub(r'^\d+\.\s+', '', safe_line), cur_h2))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC'), spaceBefore=2, spaceAfter=6))
            elif safe_line.startswith("  - ") or safe_line.startswith("   - "):
                story.append(Paragraph(safe_line.replace("- ", "", 1), cur_bullet, bulletText='◦'))
            elif safe_line.startswith("- "):
                story.append(Paragraph(safe_line.replace("- ", "", 1), cur_bullet, bulletText='•'))
            else:
                story.append(Paragraph(safe_line, cur_body))

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

# ==========================================
# THE 5-PILLAR MATH ENGINE (Street Astrologer Matrix)
# ==========================================
def calculate_planet_ecosystem(p_name, p_data, houses, planets_full, sign_lords, asc_sign, sun_lon):
    """Calculates the 5-Pillar State Matrix for a single planet."""
    
    # 1. Positional
    sign = p_data["sign"]
    house = get_house_of_planet(houses, p_name)
    dignity = p_data["dignity"]
    lon = p_data["lon"]
    deg_in_sign = lon % 30
    
    # 2. Dispositor & Nakshatra Lord
    dispositor = sign_lords.get(sign, "")
    dispositor_house = get_house_of_planet(houses, dispositor) if dispositor else None
    nak_lord = p_data.get("nak_lord", "Unknown")
    nak_lord_house = get_house_of_planet(houses, nak_lord) if nak_lord != "Unknown" else None
    
    # 3. Functional Nature (Simplified)
    func_nature = "Functional Neutral"
    p_sign_idx = ZODIAC_SIGNS.index(sign)
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    houses_ruled = []
    for i in range(12):
        if sign_lords.get(ZODIAC_SIGNS[(asc_idx + i) % 12], "") == p_name:
            houses_ruled.append(i + 1)
            
    if any(h in [1, 4, 7, 10] for h in houses_ruled) and any(h in [5, 9] for h in houses_ruled):
        func_nature = "Yoga Karaka (Highly Benefic)"
    elif any(h in [6, 8, 12] for h in houses_ruled):
        func_nature = "Functional Malefic / Maraka"
        
    # 4. Temporal (Paksha Bala for Moon)
    temporal = "Direct"
    if p_data.get("combust"): temporal = "Combust (Asta)"
    elif p_data.get("retro"): temporal = "Retrograde (Vakri)"
    
    paksha = ""
    if p_name == "Moon (Chandra)":
        dist_to_sun = abs(lon - sun_lon)
        if dist_to_sun > 180: dist_to_sun = 360 - dist_to_sun
        if dist_to_sun < 12: paksha = " (Mrita/Dead - Close to Sun)"
        elif dist_to_sun < 45: paksha = " (Weak Phase)"
        else: paksha = " (Strong Phase)"
        
    temporal += paksha

    # 5. Assaults (Aspects & Conjunctions)
    assaults = []
    # Conjunctions
    if house:
        for other_p in houses[house]["occupants"]:
            if other_p != p_name:
                assaults.append(f"Conjunct {other_p}")
                
    # Aspects
    for other_p, other_data in planets_full.items():
        if other_p == p_name: continue
        other_house = get_house_of_planet(houses, other_p)
        if other_house:
            aspected_houses = get_aspects(other_p, other_house)
            if house in aspected_houses:
                # Check Orb
                orb = abs(lon - other_data["lon"])
                if orb > 180: orb = 360 - orb
                orb_strength = "Exact" if orb < 3 else "Strong" if orb < 7 else "Wide"
                assaults.append(f"Aspected by {other_p} ({orb_strength} aspect)")
                
    # Planetary War (Graha Yuddha)
    if p_name not in ["Sun (Surya)", "Moon (Chandra)", "Rahu", "Ketu"]:
        for other_p, other_data in planets_full.items():
            if other_p == p_name or other_p in ["Sun (Surya)", "Moon (Chandra)", "Rahu", "Ketu"]: continue
            dist = abs(lon - other_data["lon"])
            if dist > 180: dist = 360 - dist
            if dist < 1.0:
                assaults.append(f"Planetary War (Graha Yuddha) with {other_p}!")
                
    return f"""- **Ecosystem for {p_name}:**
  - Position: House {house} ({HINDI_SIGNS.get(sign, sign)}), {dignity}. Degree: {deg_in_sign:.2f}°
  - Functional Nature: {func_nature} (Rules Houses: {houses_ruled if houses_ruled else 'N/A'})
  - Dispositor: {dispositor} is in House {dispositor_house}.
  - Nakshatra Lord: {nak_lord} is in House {nak_lord_house}.
  - Temporal State: {temporal}
  - Assaults: {', '.join(assaults) if assaults else 'None'}"""

def calculate_chart_logic(asc_sign, planets_full, birth_dt, sun_lon):
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
    
    # Inject the 5-Pillar Ecosystem Matrix for all planets
    logic_summary += "\n[PLANETARY ECOSYSTEM MATRIX (5-PILLAR STATE)]\n"
    for p_name, p_data in planets_full.items():
        logic_summary += calculate_planet_ecosystem(p_name, p_data, houses, planets_full, sign_lords, asc_sign, sun_lon) + "\n"

    inferences = []
    asc_lord = sign_lords.get(asc_sign)
    asc_lord_dignity = planets_full.get(asc_lord, {}).get("dignity", "Neutral")
    
    if asc_lord_dignity.startswith("Debilitated"): inferences.append("High Risk of Psychological Vitality Loss: Lagna Lord is Debilitated, structurally weakening core self-esteem and vitality.")
    if planets_full["Moon (Chandra)"]["dignity"].startswith("Debilitated"): inferences.append("High Risk of Nervous System Burnout: Moon is Debilitated, indicating chronic emotional volatility and anxiety.")
    
    if "Saturn (Shani)" in houses[2]["occupants"] and planets_full["Saturn (Shani)"]["combust"]:
        inferences.append("High Risk of Liquidity Freeze & Wealth Erosion: Saturn is Combust in the 2nd House (Wealth), severely damaging financial discipline and retention.")
        
    if houses[10]["ruler_placed_in"] in [8, 12]:
        inferences.append("High Risk of Career Collapse: 10th Lord is in the 8th or 12th House, indicating sudden career termination or structural instability.")

    yogas = detect_yogas(houses, planets_full, sign_lords)

    if houses[2]["ruler_placed_in"] in [6, 8, 12] or houses[11]["ruler_placed_in"] in [6, 8, 12]:
        yogas.append("Daridra Yoga (Poverty Yoga): 2nd or 11th Lord is in a Dusthana (6/8/12). This confirms the structural root of the liquidity freeze and severe wealth erosion.")

    for p_name in ["Mars (Mangal)", "Mercury (Budh)", "Jupiter (Guru)", "Venus (Shukra)", "Saturn (Shani)"]:
        if p_name in planets_full:
            p_house = get_house_of_planet(houses, p_name)
            p_dignity = planets_full[p_name]["dignity"]
            if p_house in [1, 4, 7, 10] and ("Own Sign" in p_dignity or "Exalted" in p_dignity):
                yogas.append(f"Panch Mahapurusha Yoga ({p_name.split(' ')[0]} in Kendra): Exceptional potential in its domain, but requires harnessing amidst the current crisis.")

    moon_nak = planets_full["Moon (Chandra)"]["nak"]
    moon_pada = planets_full["Moon (Chandra)"]["pada"]
    moon_trait = get_nak_pada_trait(moon_nak, moon_pada)
    logic_summary += f"\n[PSYCHOLOGICAL ARCHETYPE]: Moon in {moon_nak} Pada {moon_pada} grants a '{moon_trait}' core emotional nature."

    lal_kitab_rules = get_lal_kitab_remedy(houses, planets_full)
    
    logic_summary += f"\n[PRE-CALCULATED YOGAS]:\n - " + "\n - ".join(yogas) if yogas else "\n[PRE-CALCULATED YOGAS]: None."
    logic_summary += f"\n[HARD DEDUCTIVE INFERENCES]:\n - " + "\n - ".join(inferences) if inferences else "\n[HARD DEDUCTIVE INFERENCES]: None."
    logic_summary += f"\n[MANDATORY LAL KITAB REMEDY]:\n - " + "\n - ".join(lal_kitab_rules) if lal_kitab_rules else "\n[MANDATORY LAL KITAB REMEDY]: None."

    transit_data = calculate_multi_transits(planets_full["Moon (Chandra)"]["sign"], asc_sign)
    logic_summary += f"\n[LIVE TRANSIT MATRIX]:\n{transit_data}"

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
            
        d9_sign_idx = calculate_divisional_sign(lon_val, 9, sign_idx); d9_sign_name = ZODIAC_SIGNS[d9_sign_idx % 12]
        d7_sign_idx = calculate_divisional_sign(lon_val, 7, sign_idx); d7_sign_name = ZODIAC_SIGNS[d7_sign_idx % 12]
        d10_sign_idx = calculate_divisional_sign(lon_val, 10, sign_idx); d10_sign_name = ZODIAC_SIGNS[d10_sign_idx % 12]
        
        is_vargottama = (sign_name == d9_sign_name)
        shadbala = calculate_shadbala_lite(name, sign_name, is_retro, is_combust, lon_val)
        
        positions[name] = {
            "sign": sign_name, "hindi_sign": HINDI_SIGNS[sign_name], "lon": lon_val % 360.0, 
            "nak": nak_name, "nak_lord": nak_lord, "pada": pada, 
            "dignity": dignity, "retro": is_retro, "combust": is_combust, 
            "vargottama": is_vargottama, "jaimini": "",
            "d7_sign": d7_sign_name, "d10_sign": d10_sign_name, 
            "shadbala": shadbala
        }
        d9_positions[name] = {"sign": d9_sign_name, "hindi_sign": HINDI_SIGNS[d9_sign_name]}
        
    try: 
        _, ascmc = swe.houses_ex(jdut, lat, lon, b'W', flags); asc_lon = ascmc[0] % 360.0
    except: 
        asc_lon = 0.0
        
    asc_sign = ZODIAC_SIGNS[int(asc_lon / 30) % 12]; _, asc_nak, asc_pada, _ = get_nakshatra_info(asc_lon)
    asc_d9_sign_idx = calculate_divisional_sign(asc_lon, 9, ZODIAC_SIGNS.index(asc_sign)); asc_d9_sign = ZODIAC_SIGNS[asc_d9_sign_idx % 12]
    
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
    logic_breakdown, age = calculate_chart_logic(asc_sign, positions, dt_ist, sun_lon)
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
            return " [REDACTED: HALLUCINATED ASPECT] "
        clean_text = re.sub(pattern, replace_func, clean_text)
        
    forbidden_words = ["potentially", "possibly", "suggesting", "assuming", "self-care", "date nights", "yoga", "meditation", "mindfulness"]
    for word in forbidden_words:
        clean_text = re.compile(re.escape(word), re.IGNORECASE).sub("[CLINICAL REDACTION]", clean_text)
        
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
                
                planet_summary = "\n".join([
                    f"- {p}: {d['hindi_sign']} | Nak: {d['nak']} (ruled by {d.get('nak_lord', 'Unknown')}) | Dignity: {d['dignity']} | Shadbala: {d.get('shadbala', 'N/A')} {'[Vargottama]' if d.get('vargottama') else ''} | {d['jaimini']}" 
                    if d.get('jaimini') else 
                    f"- {p}: {d['hindi_sign']} | Nak: {d['nak']} (ruled by {d.get('nak_lord', 'Unknown')}) | Dignity: {d['dignity']} | Shadbala: {d.get('shadbala', 'N/A')} {'[Vargottama]' if d.get('vargottama') else ''}" 
                    for p, d in planets.items()
                ])
                
                USER_SESSIONS[chat_id] = {
                    "state": "awaiting_partner",
                    "asc_sign": asc_sign, "planet_summary": planet_summary,
                    "planet_data": planets, "d9_planets": d9_planets, "asc_d9_sign": asc_d9_sign, "t_ctx": t_ctx, "logic_breakdown": logic_breakdown, "age": age, "name": name_str,
                    "d1_svg": generate_svg_chart(f"d1_{chat_id}_{int(time.time())}", "Rasi (D1)", asc_sign, planets),
                    "d9_svg": generate_svg_chart(f"d9_{chat_id}_{int(time.time())}", "Navamsha (D9)", asc_d9_sign, d9_planets),
                    "birth_str": f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean} (Age: {age})"
                }
                send_message(chat_id, "✅ Chart calculated. \n\nDo you want to analyze compatibility with a partner? \nSend their details (Name DD-MM-YYYY HH:MM City) or type 'skip'.")
                return jsonify(status="success"), 200

            elif chat_id in USER_SESSIONS and USER_SESSIONS[chat_id].get("state") == "awaiting_partner":
                if user_text.lower() == 'skip':
                    session = USER_SESSIONS[chat_id]
                    session["state"] = "ready_to_generate"
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

# ==========================================
# CONSOLIDATED 2-AGENT PIPELINE (Deep Correlation Narrative)
# ==========================================
def call_groq_agent(groq_url, groq_key, model_name, system_msg, user_msg):
    payload = {"model": model_name, "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}], "temperature": 0.3}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
    try:
        res = requests.post(groq_url, headers=headers, json=payload, timeout=180)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        return f"[ERROR IN AGENT: {res.text[:100]}]"
    except Exception as e:
        return f"[AGENT TIMEOUT/ERROR: {str(e)}]"

def generate_final_pdf(chat_id, session, groq_key, groq_url):
    send_message(chat_id, "⏳ Initiating Deep Correlation Audit Pipeline...")
    
    model_main = "llama-3.3-70b-versatile"
    model_translator = "llama-3.1-8b-instant"

    system_msg = """You are an Elite Forensic Astrological Diagnostician writing an institutional Threat Matrix Dossier. 
[ABSOLUTE LAWS - VIOLATION = FAILURE]
1. NARRATIVE FLOW: You must follow the Temporal-Psychological flow. Establish the Psychological Baseline -> Diagnose the Past -> Pinpoint the Present Trigger -> Map the Future Survival. 
2. NO REPETITION (THE "ESTABLISHED" RULE): State the "Astronomical Root" of a crisis ONCE. In subsequent sections, do NOT re-explain the planetary placement. Use the phrase: "As established by the [Planet] placement..." and jump straight to the systemic manifestation.
3. DEEP CORRELATION: Synthesize data across houses. Link the 5-Pillar Ecosystem data to the real-world manifestations.
4. SEPARATION OF CONCERNS: Ayurvedic analysis and Lal Kitab remedies MUST be in their own dedicated sections, not merged into the Threat Vectors.
5. FORBIDDEN CONCEPTS: Do not use 'potentially', 'possibly', 'suggesting', 'assuming', 'meditation', 'mindfulness', 'self-care'. 
6. HINDI MANDATORY: Use Hindi names for EVERY Zodiac Sign and Planet.
"""

    logic = session['logic_breakdown']
    
    def extract_house_facts(house_num):
        match = re.search(rf"- House {house_num} \((.*?)\): Ruled by (.*?)\. .*? is sitting in House (\d+)\. Occupied by: (.*?)\. Aspected by: (.*?)\.", logic)
        if match:
            sign, lord, lord_house, occ, asp = match.groups()
            return f"House {house_num} is {sign}. Ruled by {lord}. Lord is in House {lord_house}. Occupied by: {occ}. Aspected by: {asp}."
        return f"Data for House {house_num} not found."

    h1_facts = extract_house_facts(1); h2_facts = extract_house_facts(2); h3_facts = extract_house_facts(3)
    h4_facts = extract_house_facts(4); h5_facts = extract_house_facts(5); h6_facts = extract_house_facts(6)
    h7_facts = extract_house_facts(7); h8_facts = extract_house_facts(8); h9_facts = extract_house_facts(9)
    h10_facts = extract_house_facts(10); h11_facts = extract_house_facts(11); h12_facts = extract_house_facts(12)

    synastry_block = ""
    if "synastry" in session:
        synastry_block = f"""
# PART 3: COMPATIBILITY & SYNESTRY ANALYSIS
- Analyze the compatibility data provided below. Explain the psychological and karmic implications of any Doshas detected.
{session.get('synastry', '')}
"""

    # SINGLE MEGA-PROMPT FOR DEEP CORRELATION NARRATIVE
    user_msg_eng = f"""[INPUT DATA]
- Baseline Date: {session['t_ctx']['current_date']}
- Exact Dasha Timeline: {session['t_ctx']['dasha_timeline']}
{session['logic_breakdown']}
[PLANETARY ARRAY]
Ascendant (Lagna): {HINDI_SIGNS[session['asc_sign']]}
{session['planet_summary']}

[OUTPUT TEMPLATE - FOLLOW EXACTLY]
*Disclaimer: This audit maps karmic tendencies and probabilistic risk vectors based on planetary mathematics. Astrological indications are environmental influences, not absolute mandates.*

# I. THE TEMPORAL-PSYCHOLOGICAL NARRATIVE (The Core Diagnosis)
- **The Psychological Baseline (Phase 1):** Explicitly name the Atmakaraka and diagnose the native's core psychological bottleneck based on the 5-Pillar Ecosystem Matrix (Dispositor/Nakshatra Lord states). How do they process stress?
- **The Historical Trajectory (Phase 2):** Analyze the Past Antardasha. What was the native experiencing leading up to this moment? Do not predict the future yet.
- **The Present Trigger (Phase 3):** Pinpoint the exact trigger. Why has the historical trajectory collapsed *right now*? Merge the Current Pratyantardasha with the Live Sade Sati/Transit data. How is this attacking their specific psychological bottleneck?
- **The Expected State & Survival (Phase 4):** Map the survival trajectory. When does this trigger end? What is the next planetary shift (Future Antardasha), and what behavioral modification is required to survive until then?

# II. THE 3-PILLAR THREAT MATRIX & DEDUCTIVE TRIAGE
*(Analyze the following domains using the strict 4-part Chain of Deduction: Astronomical Root -> Systemic Vulnerability -> Real-World Manifestation -> Tactical Countermeasure. DO NOT re-explain placements across pillars. Use "As established by..." to correlate)*

**Pillar 1: Wealth, Career & Structural Stability**
- [FACT BLOCKS]: H2: {h2_facts} | H10: {h10_facts} | H11: {h11_facts}
- **Astronomical Root:** (Correlate Dignities, Amatyakaraka, Functional Nature, Dispositor chain)
- **Systemic Vulnerability:** (Mechanical flaws in wealth/career)
- **Real-World Manifestation:** (Diagnose liquidity freezes or career stagnation)
- **Tactical Countermeasure:** (Financial triage + Gemstone/Metal prescriptions. Do NOT put Lal Kitab here, it goes in Section IV)

**Pillar 2: Relationship, Property & Progeny Dynamics**
- [FACT BLOCKS]: H4: {h4_facts} | H5: {h5_facts} | H7: {h7_facts} | H9: {h9_facts}
- **Astronomical Root:** (Correlate to Pillar 1. e.g., "The financial pressure established in Pillar 1 is bleeding into H4/H7...")
- **Systemic Vulnerability:** (Psychological friction, asset risk, progeny delays)
- **Real-World Manifestation:** (Marital alienation, property disputes, creative stagnation)
- **Tactical Countermeasure:** (Environmental/Vastu corrections + Behavioral adjustments)

**Pillar 3: Core Vitality & Subconscious Trajectory (D9)**
- [FACT BLOCKS]: H1: {h1_facts} | H3: {h3_facts} | D9 Lagna: {HINDI_SIGNS[session['asc_d9_sign']]}
- **Astronomical Root:** (Correlate to Lagna Lord dignity and D1 vs D9 shifts)
- **Systemic Vulnerability:** (Physical burnout, hidden subconscious patterns, late-life shifts)
- **Real-World Manifestation:** (Lack of initiative, internal emptiness despite external success)
- **Tactical Countermeasure:** (Physical routines + Spiritual realignment + D9 remedies)

# III. AYURVEDIC & NEUROLOGICAL AUDIT (SEPARATE & HIGHLIGHTED)
*(This section is strictly dedicated to the physical and neurological manifestation of the astrological afflictions. Do NOT mix with career or wealth).*
- **Dosha Analysis:** Based on Ascendant and Moon Dosha, diagnose the exact physical imbalance (Vata/Pitta/Kapha).
- **Neurological Breakdown:** Link the Moon's Paksha Bala (strength) and the Assault Vectors (Aspects/Combustion) to exact clinical symptoms (e.g., panic attacks, insomnia, adrenal fatigue).
- **Ayurvedic Triage Protocol:** Prescribe specific dietary shifts (e.g., warm grounding foods for Vata), lifestyle modifications, and targeted herbal/routine recommendations to hack the nervous system.

# IV. WHOLISTIC LAL KITAB REMEDIATION & ALIGNMENT (SEPARATE & HIGHLIGHTED)
*(This section compiles ALL Lal Kitab rules into a single, chronological treatment plan. Do NOT invent remedies. Use the [MANDATORY LAL KITAB REMEDY] section verbatim).*
- **Immediate First Aid:** The most urgent karmic actions to stop the bleeding (based on the most severe afflictions).
- **Holistic Protocol:** Compile the remaining Lal Kitab remedies into a clear, weekly schedule.
- **Long-Term Mantras:** Specific mantras for the Lagna Lord or afflicted planets to rebuild self-worth and survive the upcoming Future Dasha.
{synastry_block}
"""

    # Execute Agent 1 (English Master Synthesizer)
    send_message(chat_id, "⏳ Master Synthesizer Agent drafting deep-correlation dossier...")
    english_text = call_groq_agent(groq_url, groq_key, model_main, system_msg, user_msg_eng)
    
    if "[ERROR IN AGENT" in english_text or "[AGENT TIMEOUT" in english_text:
        send_message(chat_id, "⚠️ Master Agent failed. Sending raw data instead.")
        send_message(chat_id, english_text)
        return jsonify(status="error"), 500

    final_text_firewalled = llm_output_firewall(english_text, logic)
    
    # Execute Agent 2 (Hindi Translator) using the cheaper/faster 8B model
    send_message(chat_id, "⏳ Translating to Hindi (Fast Model)...")
    translator_system_msg = """You are an expert astrological translator. Translate the provided English astrological dossier into formal, clinical Hindi. 
    Maintain all Markdown formatting (**, ###, -, #). 
    Ensure ALL astrological terms have their Hindi names in brackets (e.g., Saturn (Shani), 2nd House (द्वितीय भाव)). 
    Do not add or remove information. Translate exactly."""
    
    hindi_text = call_groq_agent(groq_url, groq_key, model_translator, translator_system_msg, f"Translate the following text to Hindi:\n\n{final_text_firewalled}")
    
    if "[AGENT TIMEOUT/ERROR" in hindi_text or "[ERROR IN AGENT" in hindi_text:
        hindi_text = "Hindi translation failed due to API timeout. Please refer to the English dossier above."
    
    complete_pdf_text = final_text_firewalled + "\n\n# PART 2: हिंदी अनुवाद (HINDI TRANSLATION)\n\n" + hindi_text
    
    # PDF Generation
    send_message(chat_id, "⏳ Compiling Forensic Dossier PDF...")
    file_tag = str(int(time.time()))
    pdf_path = f"/tmp/Astrological_Audit_{file_tag}.pdf"
    
    pdf_success = False
    hindi_font_loaded = False
    try:
        font_path = "/tmp/Mukta-Regular.ttf"
        if not os.path.exists(font_path):
            font_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/mukta/Mukta-Regular.ttf"
            req = urllib.request.Request(font_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response, open(font_path, 'wb') as out_file:
                out_file.write(response.read())
        
        pdfmetrics.registerFont(TTFont('MuktaDevanagari', font_path))
        hindi_font_loaded = True
        
    except Exception as e:
        print(f"Hindi Font Registration Failed: {e}.", flush=True)
        
    try:
        if hindi_font_loaded:
            pdf_success = generate_master_pdf(complete_pdf_text, pdf_path, session["birth_str"], session["name"], session["planet_data"], session["asc_sign"], session["d9_planets"], session["asc_d9_sign"], hindi_font_name='MuktaDevanagari')
        else:
            pdf_success = generate_master_pdf(final_text_firewalled, pdf_path, session["birth_str"], session["name"], session["planet_data"], session["asc_sign"], session["d9_planets"], session["asc_d9_sign"])
            
    except Exception as e:
        print(f"PDF Compilation Error: {e}", flush=True)
        pdf_success = generate_master_pdf(final_text_firewalled, pdf_path, session["birth_str"], session["name"], session["planet_data"], session["asc_sign"], session["d9_planets"], session["asc_d9_sign"])
        
    if pdf_success and os.path.exists(pdf_path):
        send_document(chat_id, pdf_path)
        send_message(chat_id, "📄 **Astrological Audit PDF attached above!** ⬆️\nYou can now ask specific tactical questions based on this audit.")
        
        if not hindi_font_loaded:
            txt_path = f"/tmp/Hindi_Translation_{file_tag}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(hindi_text)
            send_document(chat_id, txt_path)
            
    else:
        send_message(chat_id, "⚠️ PDF generation failed. Sending text report:")
        for i in range(0, len(complete_pdf_text), 3900): send_message(chat_id, complete_pdf_text[i:i + 3900]); time.sleep(0.5)
        
    return jsonify(status="success"), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
