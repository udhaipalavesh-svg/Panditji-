# ==========================================
# CELESTIAL STRATEGY BOT - MONOLITHIC ARCHITECTURE
# ==========================================
import os
import requests
import json
import time
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# Note: You will need to make sure these are in your requirements.txt:
# Flask==3.0.0
# requests==2.31.0
# pyswisseph==2.10.3.2
# weasyprint==61.1

# ==========================================
# PART 1: DATA WAREHOUSE (Constants, BAV, Lal Kitab)
# (I will provide this block next)
# ==========================================
# ==========================================
# PART 1: DATA WAREHOUSE (Constants, BAV, Lal Kitab)
# ==========================================

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

HINDI_SIGNS = {
    "Aries": "Aries / Mesha", "Taurus": "Taurus / Vrishabha", "Gemini": "Gemini / Mithuna", 
    "Cancer": "Cancer / Karka", "Leo": "Leo / Simha", "Virgo": "Virgo / Kanya", 
    "Libra": "Libra / Tula", "Scorpio": "Scorpio / Vrishchika", "Sagittarius": "Sagittarius / Dhanu", 
    "Capricorn": "Capricorn / Makara", "Aquarius": "Aquarius / Kumbha", "Pisces": "Pisces / Meena"
}

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", 
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", 
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", 
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", 
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

DASHA_LORDS = [
    ("Ketu / Ketu", 7), ("Venus / Shukra", 20), ("Sun / Surya", 6), 
    ("Moon / Chandra", 10), ("Mars / Mangal", 7), ("Rahu / Rahu", 18), 
    ("Jupiter / Guru", 16), ("Saturn / Shani", 19), ("Mercury / Budh", 17)
]

EXALTATION = {
    "Sun / Surya": "Aries", "Moon / Chandra": "Taurus", "Mars / Mangal": "Capricorn", 
    "Mercury / Budh": "Virgo", "Jupiter / Guru": "Cancer", "Venus / Shukra": "Pisces", 
    "Saturn / Shani": "Libra", "Rahu / Rahu": "Taurus", "Ketu / Ketu": "Scorpio"
}

DEBILITATION = {
    "Sun / Surya": "Libra", "Moon / Chandra": "Scorpio", "Mars / Mangal": "Cancer", 
    "Mercury / Budh": "Pisces", "Jupiter / Guru": "Capricorn", "Venus / Shukra": "Virgo", 
    "Saturn / Shani": "Aries", "Rahu / Rahu": "Scorpio", "Ketu / Ketu": "Taurus"
}

OWN_SIGNS = {
    "Sun / Surya": ["Leo"], "Moon / Chandra": ["Cancer"], "Mars / Mangal": ["Aries", "Scorpio"], 
    "Mercury / Budh": ["Gemini", "Virgo"], "Jupiter / Guru": ["Sagittarius", "Pisces"], 
    "Venus / Shukra": ["Taurus", "Libra"], "Saturn / Shani": ["Capricorn", "Aquarius"]
}

COMBUSTION_ORB = {
    "Moon / Chandra": 12, "Mars / Mangal": 17, "Mercury / Budh": 14, 
    "Jupiter / Guru": 11, "Venus / Shukra": 10, "Saturn / Shani": 15
}

BAV_TABLES = {
    "Sun / Surya": [0,0,1,1,0,0,1,1, 1,0,0,0,1,1,0,0, 0,1,1,0,0,1,1,0, 0,0,1,1,0,0,1,1, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 0,0,0,1,1,1,1,0, 1,1,1,0,0,0,0,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0],
    "Moon / Chandra": [0,1,0,1,1,0,1,0, 1,0,1,0,0,1,0,1, 1,1,0,0,1,1,0,0, 0,1,1,0,1,0,1,0, 1,0,1,1,0,1,0,1, 0,1,0,1,1,0,1,0, 1,1,0,1,0,1,1,0, 0,0,1,1,1,1,0,0, 1,1,0,0,0,0,1,1, 0,0,1,1,1,1,0,0, 1,0,1,0,0,1,0,1, 0,1,0,1,1,0,1,0],
    "Mars / Mangal": [1,0,0,1,1,0,0,1, 1,1,0,0,1,1,0,0, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 0,1,1,0,1,0,1,0, 1,0,1,0,0,1,0,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,0,1,1,1,1,0],
    "Mercury / Budh": [0,1,1,0,1,0,0,1, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,1,0,0,1,1,0,0],
    "Jupiter / Guru": [0,1,1,1,0,0,0,0, 1,0,0,0,1,1,1,0, 1,1,0,0,0,0,1,1, 0,0,1,1,1,1,0,0, 1,1,1,0,0,0,0,1, 0,0,0,1,1,1,1,0, 0,1,1,0,1,0,1,0, 1,0,0,1,0,1,0,1, 0,1,1,1,0,0,0,0, 1,0,0,0,1,1,1,0, 0,0,0,1,1,1,1,0, 1,1,1,0,0,0,0,1],
    "Venus / Shukra": [1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 0,1,1,0,1,0,1,0, 1,0,0,1,0,1,0,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0],
    "Saturn / Shani": [0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,0,0,1,1,0, 0,1,0,1,1,0,0,1, 1,0,1,0,1,0,0,1, 0,1,0,1,0,1,1,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0]
}

VEDIC_MANTRAS = {
    "Sun / Surya": "Om Hraam Hreem Hroum Sah Suryaya Namah", 
    "Moon / Chandra": "Om Shraam Shreem Shroum Sah Chandraya Namah",
    "Mars / Mangal": "Om Kraam Kreem Kroum Sah Bhaumaya Namah", 
    "Mercury / Budh": "Om Braam Breem Broum Sah Budhaya Namah",
    "Jupiter / Guru": "Om Graam Greem Groum Sah Gurve Namah", 
    "Venus / Shukra": "Om Draam Dreem Droum Sah Shukraya Namah",
    "Saturn / Shani": "Om Praam Preem Proum Sah Shanaishcharaya Namah", 
    "Rahu / Rahu": "Om Bhraam Bhreem Bhroum Sah Rahave Namah",
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

# EXTENSIVE LAL KITAB DICTIONARY
LAL_KITAB_DICT = {
    # Dignity and Condition Modifiers
    "Saturn / Shani_Combust": "Donate black sesame oil on Saturday.", "Mars / Mangal_Combust": "Avoid keeping iron tools under the bed.",
    "Jupiter / Guru_Combust": "Apply a tilak of saffron on the forehead daily.", "Venus / Shukra_Combust": "Donate pure ghee to a temple on Friday.",
    "Mercury / Budh_Combust": "Clean teeth with fitkari (alum) daily.", "Sun / Surya_Debilitated": "Offer water to the Sun. Avoid salt on Sundays.",
    "Moon / Chandra_Debilitated": "Immerse a square piece of silver in a river on Monday.", "Mars / Mangal_Debilitated": "Float red copper in a flowing river on Tuesday.",
    "Mercury / Budh_Debilitated": "Avoid wearing green clothes. Keep broad-leaved plants away.", "Jupiter / Guru_Debilitated": "Water a peepal tree on Thursday.",
    "Venus / Shukra_Debilitated": "Donate white sweets to young girls on Friday.", "Saturn / Shani_Debilitated": "Serve food to disabled people on Saturday.",
    "Rahu / Rahu_Debilitated": "Keep a square silver piece in your pocket.", "Ketu / Ketu_Debilitated": "Feed a two-colored dog.",
    
    # Sun / Surya
    "Sun / Surya_1": "Offer sweetened water to the Sun daily.", "Sun / Surya_2": "Donate wheat and jaggery in a temple on Sunday.",
    "Sun / Surya_3": "Maintain respectful and supportive relations with younger siblings.", "Sun / Surya_4": "Do not consume salt on Sundays; feed bread to street dogs.",
    "Sun / Surya_5": "Keep a red handkerchief in your pocket at all times.", "Sun / Surya_6": "Feed a red cow on Sundays and respect your maternal uncles.",
    "Sun / Surya_7": "Reduce anger in partnerships; avoid taking the first aggressive step.", "Sun / Surya_8": "Keep a copper pot filled with water in the southern part of the home.",
    "Sun / Surya_9": "Use brass utensils for eating and respect your ancestors.", "Sun / Surya_10": "Wear a copper coin around your neck on a white thread.",
    "Sun / Surya_11": "Drink water exclusively from a copper vessel.", "Sun / Surya_12": "Keep the courtyard or entrance of your home meticulously clean.",

    # Moon / Chandra
    "Moon / Chandra_1": "Drink milk or water from a silver glass.", "Moon / Chandra_2": "Keep a square piece of silver in your house.",
    "Moon / Chandra_3": "Offer green gram (moong dal) to birds or plant a fruit-bearing tree.", "Moon / Chandra_4": "Do not trade in milk or dairy products.",
    "Moon / Chandra_5": "Serve your mother and seek her blessings before major decisions.", "Moon / Chandra_6": "Serve water to patients in a hospital or set up a public water cooler.",
    "Moon / Chandra_7": "Do not marry before the age of 24. Avoid milk business.", "Moon / Chandra_8": "Immerse a silver coin in a flowing river.",
    "Moon / Chandra_9": "Visit religious places frequently and offer milk at a temple.", "Moon / Chandra_10": "Avoid drinking milk at night. Store rainwater in a bottle.",
    "Moon / Chandra_11": "Donate milk to a temple on Mondays and distribute sweets to children.", "Moon / Chandra_12": "Store rainwater in a glass bottle with a silver lid at home.",

    # Mars / Mangal
    "Mars / Mangal_1": "Avoid keeping large or rusted weapons in the house.", "Mars / Mangal_2": "Donate red masoor dal and batasha on Tuesday.",
    "Mars / Mangal_3": "Wear a silver ring on your left hand. Avoid accepting free gifts.", "Mars / Mangal_4": "Keep a square piece of red copper in the house.",
    "Mars / Mangal_5": "Keep a pot of water by your bedside and pour it on a plant in the morning.", "Mars / Mangal_6": "Donate red clothes or red sweets to young girls.",
    "Mars / Mangal_7": "Build a solid boundary wall around your home. Offer sweets to your sister.", "Mars / Mangal_8": "Feed sweet roti cooked in a tandoor to a dog.",
    "Mars / Mangal_9": "Offer milk to a banyan tree and apply the wet mud as a tilak.", "Mars / Mangal_10": "Offer sweet milk to a blind person.",
    "Mars / Mangal_11": "Keep a red handkerchief in your pocket. Do not sell ancestral property.", "Mars / Mangal_12": "Float a piece of red copper or honey in flowing water.",

    # Mercury / Budh
    "Mercury / Budh_1": "Avoid wearing green clothes. Do not keep broad-leaved plants indoors.", "Mercury / Budh_2": "Keep a silver box filled with rainwater and a silver piece inside.",
    "Mercury / Budh_3": "Clean your teeth with alum (fitkari) daily. Donate green moong.", "Mercury / Budh_4": "Float a copper coin in a river on Wednesday.",
    "Mercury / Budh_5": "Wear a copper coin around your neck for financial stability.", "Mercury / Budh_6": "Float an earthen pot filled with milk in a river.",
    "Mercury / Budh_7": "Respect your sisters and aunts. Do not enter into a partnership business.", "Mercury / Budh_8": "Bury an earthen pot filled with sugar in a deserted place.",
    "Mercury / Budh_9": "Feed green grass to a cow. Do not accept talismans from sadhus.", "Mercury / Budh_10": "Abstain from alcohol and non-vegetarian food.",
    "Mercury / Budh_11": "Wear a copper coin with a hole in it around your neck.", "Mercury / Budh_12": "Tie a yellow thread around your neck. Donate to an orphanage.",

    # Jupiter / Guru
    "Jupiter / Guru_1": "Apply a saffron or turmeric tilak on your forehead daily.", "Jupiter / Guru_2": "Donate yellow clothes or chana dal to a priest.",
    "Jupiter / Guru_3": "Worship Goddess Durga and offer sweets to young girls.", "Jupiter / Guru_4": "Serve your elders and gurus. Do not keep a temple inside your bedroom.",
    "Jupiter / Guru_5": "Plant a peepal tree and water it regularly.", "Jupiter / Guru_6": "Donate chana dal at a religious place. Offer water to peepal.",
    "Jupiter / Guru_7": "Tie gold in a yellow cloth and keep it in your safe.", "Jupiter / Guru_8": "Plant a peepal tree in a crematorium. Donate potatoes or camphor.",
    "Jupiter / Guru_9": "Wear gold or silver on your body. Visit temples frequently.", "Jupiter / Guru_10": "Clean your nose before starting any important work.",
    "Jupiter / Guru_11": "Float a copper coin in a river. Keep a yellow handkerchief.", "Jupiter / Guru_12": "Serve sadhus and ascetics. Do not give false witness.",

    # Venus / Shukra
    "Venus / Shukra_1": "Ensure you marry with your parents' consent and blessings.", "Venus / Shukra_2": "Keep two solid earthen potatoes (made of yellow clay) in the house.",
    "Venus / Shukra_3": "Respect women and maintain a polite demeanor. Avoid flirting.", "Venus / Shukra_4": "Throw a pinch of rice or silver in a well.",
    "Venus / Shukra_5": "Wash your private parts with curd or milk. Marry with parental consent.", "Venus / Shukra_6": "Keep a solid silver ball in your pocket. Respect your spouse.",
    "Venus / Shukra_7": "Keep a white cow or feed white cows. Avoid wearing torn clothes.", "Venus / Shukra_8": "Throw a copper coin in a gutter or dirty water drain.",
    "Venus / Shukra_9": "Bury a small square piece of silver under a neem tree.", "Venus / Shukra_10": "Wash your spouse's innerwear occasionally to wash away bad karma.",
    "Venus / Shukra_11": "Donate cotton in a temple. Keep mustard oil in an earthen pot.", "Venus / Shukra_12": "Bury a blue flower in the ground at the time of sunset.",

    # Saturn / Shani
    "Saturn / Shani_1": "Bury surma (kohl) in the ground in a deserted place.", "Saturn / Shani_2": "Walk barefoot to a temple for 43 consecutive days.",
    "Saturn / Shani_3": "Keep three dogs as pets or feed street dogs regularly.", "Saturn / Shani_4": "Do not build a house before the age of 48.",
    "Saturn / Shani_5": "Keep a portion of almonds in a temple and bring half back home.", "Saturn / Shani_6": "Float an earthen pot or glass bottle filled with mustard oil in a river.",
    "Saturn / Shani_7": "Fill a small earthen pot with honey and bury it in a deserted place.", "Saturn / Shani_8": "Drop 8 kilograms of raw coal or lead in running water.",
    "Saturn / Shani_9": "Keep a square piece of silver. Avoid wearing black or blue clothes.", "Saturn / Shani_10": "Feed black crows daily. Maintain strict punctuality and discipline.",
    "Saturn / Shani_11": "Place a vessel filled with mustard oil in a dark corner of your house.", "Saturn / Shani_12": "Tie twelve almonds in a black cloth and place them in an iron pot.",

    # Rahu / Rahu
    "Rahu / Rahu_1": "Keep a square piece of silver in your pocket or wallet.", "Rahu / Rahu_2": "Keep a solid silver ball in your pocket.",
    "Rahu / Rahu_3": "Do not keep ivory items or old, rusted iron in the house.", "Rahu / Rahu_4": "Wear a silver wire around your neck.",
    "Rahu / Rahu_5": "Keep a solid silver elephant statue in the house.", "Rahu / Rahu_6": "Keep a black dog. Float a piece of lead in running water.",
    "Rahu / Rahu_7": "Store river water in a dark glass bottle in your home.", "Rahu / Rahu_8": "Float four coconuts or 8 pieces of lead in a river on Saturday.",
    "Rahu / Rahu_9": "Apply a saffron tilak. Keep good relations with your in-laws.", "Rahu / Rahu_10": "Wear a blue or black cap. Do not keep your head uncovered.",
    "Rahu / Rahu_11": "Drink water from a silver glass. Wear an iron ring.", "Rahu / Rahu_12": "Keep a pouch of fennel (saunf) under your pillow at night.",

    # Ketu / Ketu
    "Ketu / Ketu_1": "Feed a two-colored dog (black and white).", "Ketu / Ketu_2": "Maintain absolute honesty in financial ledgers. Apply a saffron tilak.",
    "Ketu / Ketu_3": "Float rice mixed with milk in a river. Apply a saffron tilak.", "Ketu / Ketu_4": "Throw a piece of gold in flowing water (or keep it in a water pot).",
    "Ketu / Ketu_5": "Donate milk and sugar. Donate a black and white blanket.", "Ketu / Ketu_6": "Wear a gold ring on the left hand. Drink milk with saffron.",
    "Ketu / Ketu_7": "Do not make false promises. Keep a piece of iron dipped in water.", "Ketu / Ketu_8": "Feed street dogs regularly. Donate a black and white blanket at a temple.",
    "Ketu / Ketu_9": "Keep a gold brick or coin in the house. Respect the elders.", "Ketu / Ketu_10": "Keep a silver pot filled with honey in the house.",
    "Ketu / Ketu_11": "Keep a radish near your bed at night and donate it in the morning.", "Ketu / Ketu_12": "Do not keep broken jewelry. Keep a dog as a pet.",
    # Major Dosha Remedies
    "Mangalik Dosha": "Keep a square piece of silver. Feed sweet roti to crows or street dogs. Avoid accepting free gifts.",
    "Shani Sade Sati": "Pour milk on a Banyan tree root and apply the wet soil as a tilak. Do not consume alcohol or non-vegetarian food.",
    "Kemadruma Yoga": "Keep a solid silver square in your wallet. Drink water exclusively from a silver vessel.",
    "Kaal Sarp Dosha": "Float a silver metallic snake in running river water. Wear a silver ring on the left hand.",
}


# Standard Sign Rulership Map for Dispositor logic
SIGN_RULERS = {
    "Aries": "Mars / Mangal", "Taurus": "Venus / Shukra", "Gemini": "Mercury / Budh",
    "Cancer": "Moon / Chandra", "Leo": "Sun / Surya", "Virgo": "Mercury / Budh",
    "Libra": "Venus / Shukra", "Scorpio": "Mars / Mangal", "Sagittarius": "Jupiter / Guru",
    "Capricorn": "Saturn / Shani", "Aquarius": "Saturn / Shani", "Pisces": "Jupiter / Guru"
}

def check_retrograde(jdut, p_id):
    """ Extracts longitudinal speed from Swiss Ephemeris to determine retrograde status. """
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    try:
        calc = swe.calc_ut(jdut, p_id, flags)
        if isinstance(calc, tuple) and len(calc) > 0:
            if isinstance(calc[0], tuple):
                lon_speed = calc[0][3]
            else:
                lon_speed = calc[3]  
            return lon_speed < 0.0
        return False
    except Exception as e:
        print(f"Retrograde check failed for {p_id}: {e}")
        return False

def get_dispositor(planet, sign):
    """ Returns the ruler of the sign a planet is placed in. """
    return SIGN_RULERS.get(sign, "Unknown")

def calculate_karakas(positions_dict):
    """ Calculates Jaimini Atmakaraka (highest degree) and Darakaraka (lowest degree). """
    physical_planets = {
        p: data for p, data in positions_dict.items() 
        if "Rahu" not in p and "Ketu" not in p
    }
    if not physical_planets:
        return {"Atmakaraka": None, "Darakaraka": None}
    
    sorted_planets = sorted(
        physical_planets.items(), 
        key=lambda item: item[1].get("lon", 0.0) % 30.0, 
        reverse=True
    )
    return {
        "Atmakaraka": sorted_planets[0][0],
        "Darakaraka": sorted_planets[-1][0]
    }

def detect_structural_doshas(houses_dict, planet_data):
    """ Detects Major Karmic Afflictions (Doshas) based on house geometry. """
    doshas = []
    
    # Set of physical planets to check for Kemadruma (ignoring Rahu/Ketu)
    physical_planets_set = {
        "Sun / Surya", "Mars / Mangal", "Mercury / Budh", 
        "Jupiter / Guru", "Venus / Shukra", "Saturn / Shani"
    }

    # 1. Mangalik Dosha: Mars in 1, 4, 7, 8, or 12
    mangalik_houses = [1, 4, 7, 8, 12]
    for h in mangalik_houses:
        if "Mars / Mangal" in houses_dict.get(h, {}).get("occupants", []):
            doshas.append(f"Mangalik Dosha: Mars in House {h}")
            break # Flag once is sufficient for the report

    # Find Moon's house for Sade Sati and Kemadruma
    moon_house = None
    for h, data in houses_dict.items():
        if "Moon / Chandra" in data.get("occupants", []):
            moon_house = h
            break

    if moon_house:
        # Safe wrap-around for 12-to-1
        house_before = 12 if moon_house == 1 else moon_house - 1
        house_after = 1 if moon_house == 12 else moon_house + 1
        
        # 2. Shani Sade Sati: Saturn in same house, immediately before, or immediately after Moon
        sat_in_moon = "Saturn / Shani" in houses_dict[moon_house].get("occupants", [])
        sat_before = "Saturn / Shani" in houses_dict[house_before].get("occupants", [])
        sat_after = "Saturn / Shani" in houses_dict[house_after].get("occupants", [])
        
        if sat_in_moon or sat_before or sat_after:
            if sat_in_moon:
                phase = "Peak Phase"
            elif sat_before:
                phase = "Rising Phase"
            else:
                phase = "Setting Phase"
            doshas.append(f"Shani Sade Sati: Saturn in {phase} relative to natal Moon (House {moon_house})")

        # 3. Kemadruma Yoga: No physical planets in houses immediately before or after Moon
        adj_before_occupants = [p for p in houses_dict[house_before].get("occupants", []) if p in physical_planets_set]
        adj_after_occupants = [p for p in houses_dict[house_after].get("occupants", []) if p in physical_planets_set]
        
        if not adj_before_occupants and not adj_after_occupants:
            doshas.append("Kemadruma Yoga: No physical planets adjacent to natal Moon")

    return doshas
def check_neecha_bhanga(planet_name, p_data, houses_dict):
    """ Checks if a debilitated planet has cancellation of debilitation (Neecha Bhanga).
    Rule: The dispositor of the debilitated planet's sign is in a Kendra (1, 4, 7, 10). """
    if not p_data.get("dignity", "").startswith("Debilitated"):
        return False
        
    sign = p_data.get("sign")
    if not sign:
        return False
        
    dispositor = get_dispositor(planet_name, sign)
    if not dispositor or dispositor == "Unknown":
        return False
        
    for h_num, h_data in houses_dict.items():
        if dispositor in h_data.get("occupants", []):
            if h_num in [1, 4, 7, 10]:
                return True
            break
    return False

def check_kaal_sarp(houses_dict):
    """ Checks for Kaal Sarp Dosha geometry.
    Returns True if all 7 physical planets are on one side of the Rahu-Ketu axis. """
    physical_planets = {
        "Sun / Surya", "Moon / Chandra", "Mars / Mangal", 
        "Mercury / Budh", "Jupiter / Guru", "Venus / Shukra", "Saturn / Shani"
    }
    rahu_h = None
    ketu_h = None
    physical_houses = set()
    
    for h_num, h_data in houses_dict.items():
        occupants = h_data.get("occupants", [])
        if "Rahu / Rahu" in occupants:
            rahu_h = h_num
        if "Ketu / Ketu" in occupants:
            ketu_h = h_num
        # Also collect physical planets in this house
        for p in occupants:
            if p in physical_planets:
                physical_houses.add(h_num)
                
    if rahu_h is None or ketu_h is None:
        return False
        
    # Generate the two 7-house arcs (inclusive of Rahu and Ketu houses)
    arc_rahu_to_ketu = [(rahu_h + i - 1) % 12 + 1 for i in range(7)]
    arc_ketu_to_rahu = [(ketu_h + i - 1) % 12 + 1 for i in range(7)]
    
    # Check if all physical planets fall within one of the arcs
    is_arc_1 = physical_houses.issubset(set(arc_rahu_to_ketu))
    is_arc_2 = physical_houses.issubset(set(arc_ketu_to_rahu))
    
    return is_arc_1 or is_arc_2
import swisseph as swe

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

def calculate_vargas(natal_planets_dict, asc_lon):
    vargas = {}
    
    # Inject Ascendant into the calculation matrix
    temp_dict = natal_planets_dict.copy()
    temp_dict["Ascendant / Lagna"] = {"lon": asc_lon}
    
    for planet, data in temp_dict.items():
        lon = data.get("lon", 0.0) % 360.0
        sign_idx = int(lon // 30) % 12
        deg_in_sign = lon % 30
        
        # D9 Math
        if sign_idx % 3 == 0: d9_start = sign_idx
        elif sign_idx % 3 == 1: d9_start = (sign_idx + 8) % 12
        else: d9_start = (sign_idx + 4) % 12
        d9_sign_idx = (d9_start + int(deg_in_sign // (30/9))) % 12
        
        # D10 Math (Parashari)
        if sign_idx % 2 == 1: d10_start = (sign_idx + 8) % 12
        else: d10_start = sign_idx
        d10_sign_idx = (d10_start + int(deg_in_sign // 3)) % 12
        
        vargas[planet] = {"D9": ZODIAC_SIGNS[d9_sign_idx], "D10": ZODIAC_SIGNS[d10_sign_idx]}
    return vargas

def detect_yogas(houses_dict, planets_dict):
    yogas = []
    moon_house = next((h for h, d in houses_dict.items() if "Moon / Chandra" in d["occupants"]), None)
    jup_house = next((h for h, d in houses_dict.items() if "Jupiter / Guru" in d["occupants"]), None)
    if moon_house and jup_house and abs(jup_house - moon_house) in [0, 3, 6, 9]:
        yogas.append("Gaja Kesari Yoga (Jupiter in Kendra from Moon): Indicates intellectual capacity, reputation, and leadership.")
    return yogas

def detect_toxic_conjunctions(houses_dict):
    """ Detects toxic planetary conjunctions (Curses) based on same-house occupancy. """
    conjunctions = []
    for h_num, h_data in houses_dict.items():
        occ = set(h_data.get("occupants", []))
        if "Jupiter / Guru" in occ and ("Rahu / Rahu" in occ or "Ketu / Ketu" in occ):
            conjunctions.append(f"Guru Chandal Yoga: Jupiter conjunct Rahu/Ketu in House {h_num}")
        if ("Sun / Surya" in occ or "Moon / Chandra" in occ) and ("Rahu / Rahu" in occ or "Ketu / Ketu" in occ):
            conjunctions.append(f"Grahan Yoga: Sun/Moon conjunct Rahu/Ketu in House {h_num}")
        if "Moon / Chandra" in occ and "Saturn / Shani" in occ:
            conjunctions.append(f"Vish Yoga: Moon conjunct Saturn in House {h_num}")
        if "Mars / Mangal" in occ and ("Rahu / Rahu" in occ or "Ketu / Ketu" in occ):
            conjunctions.append(f"Angaraka Yoga: Mars conjunct Rahu/Ketu in House {h_num}")
    return conjunctions

def detect_mahapurusha_yogas(houses_dict, planet_data):
    """ Detects Pancha Mahapurusha Yogas. Occurs when Mars, Mercury, Jupiter, Venus, or Saturn 
    are in a Kendra (1,4,7,10) AND in their Own Sign or Exalted. """
    yogas = []
    kendras = [1, 4, 7, 10]
    mahapurusha_map = {
        "Mars / Mangal": "Ruchaka Yoga",
        "Mercury / Budh": "Bhadra Yoga",
        "Jupiter / Guru": "Hamsa Yoga",
        "Venus / Shukra": "Malavya Yoga",
        "Saturn / Shani": "Sasha Yoga"
    }

    for planet, yoga_name in mahapurusha_map.items():
        p_house = None
        for h_num, h_data in houses_dict.items():
            if planet in h_data.get("occupants", []):
                p_house = h_num
                break

        if p_house in kendras:
            dignity = planet_data.get(planet, {}).get("dignity", "")
            if dignity.startswith("Exalted") or dignity.startswith("Own Sign"):
                yogas.append(f"{yoga_name}: {planet.split('/')[0].strip()} in {dignity.split('/')[0].strip()} sign in a Kendra (House {p_house})")

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
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    
    planets_to_track = {"Saturn / Shani": swe.SATURN, "Jupiter / Guru": swe.JUPITER, "Rahu / Rahu": swe.MEAN_NODE}
    timings = []
    for name, p_id in planets_to_track.items():
        calc = swe.calc_ut(jdut, p_id, flags)
        curr_sign = int((calc[0][0] if isinstance(calc, tuple) and isinstance(calc[0], tuple) else calc[0]) / 30) % 12
        scan_jd = jdut
        for _ in range(730):
            scan_jd += 1.0
            calc_scan = swe.calc_ut(scan_jd, p_id, flags)
            scan_sign = int((calc_scan[0][0] if isinstance(calc_scan, tuple) and isinstance(calc_scan[0], tuple) else calc_scan[0]) / 30) % 12
            if scan_sign != curr_sign:
                ingress_date = swe.revjul(scan_jd)
                timings.append(f"{name} enters {ZODIAC_SIGNS[scan_sign]} on {int(ingress_date[1]):02d}/{int(ingress_date[0])}")
                # Critical Fix: Update curr_sign to track subsequent retrograde/direct ingresses
                curr_sign = scan_sign
                
    return "; ".join(timings) if timings else "No major ingress in next 2 years"
def detect_graha_yuddha(planet_data):
    """Detects Planetary War (Graha Yuddha) within 1 degree of absolute longitude."""
    wars = []
    # Only physical planets participate in war (exclude Luminaries and Nodes traditionally, but we check standard 5)
    fighters = ["Mars / Mangal", "Mercury / Budh", "Jupiter / Guru", "Venus / Shukra", "Saturn / Shani"]
    
    for i in range(len(fighters)):
        for j in range(i + 1, len(fighters)):
            p1, p2 = fighters[i], fighters[j]
            if p1 in planet_data and p2 in planet_data:
                lon1 = planet_data[p1]["lon"]
                lon2 = planet_data[p2]["lon"]
                
                # True circular distance
                diff = abs(lon1 - lon2)
                dist = min(diff, 360.0 - diff)
                
                if dist <= 1.0:
                    wars.append(f"Graha Yuddha (Planetary War): {p1.split('/')[0].strip()} and {p2.split('/')[0].strip()} are locked in exact combat within 1 degree.")
    return wars

def calculate_panchanga(jdut, sun_lon, moon_lon):
    """Calculates strict Vedic Tithi and Vaar (Weekday)."""
    tithi_num = int(((moon_lon - sun_lon) % 360.0) / 12.0) + 1
    vaar_idx = int((jdut + 1.5) % 7)
    weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    return {"Tithi": tithi_num, "Vaar": weekdays[vaar_idx]}

def calculate_kakshya(lon):
    """Calculates the True Ashtakavarga sub-division (Kakshya) Lord."""
    deg = lon % 30.0
    index = int(deg // 3.75)
    if index > 7: index = 7
    kakshya_lords = ["Saturn / Shani", "Jupiter / Guru", "Mars / Mangal", "Sun / Surya", "Venus / Shukra", "Mercury / Budh", "Moon / Chandra", "Ascendant"]
    return kakshya_lords[index]

def calculate_sidereal_chart(day, month, year, hour, minute, lat, lon):
    swe.set_ephe_path(None); swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    dt_local = datetime(year, month, day, hour, minute)
    offset_hours = lon / 15.0  # Local Mean Time (LMT) UTC offset based on longitude
    dt_utc = dt_local - timedelta(hours=offset_hours)
    jdut = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + (dt_utc.minute / 60.0))

    flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    planets = {"Sun / Surya": swe.SUN, "Moon / Chandra": swe.MOON, "Mars / Mangal": swe.MARS, "Mercury / Budh": swe.MERCURY, "Jupiter / Guru": swe.JUPITER, "Venus / Shukra": swe.VENUS, "Saturn / Shani": swe.SATURN, "Rahu / Rahu": swe.MEAN_NODE, "Ketu / Ketu": 10}
    positions = {}; rahu_lon = 0.0; sun_lon = 0.0
    
    for name, p_id in planets.items():
        is_retrograde = False
        if name == "Ketu / Ketu": 
            lon_val = (rahu_lon + 180.0) % 360.0
        else:
            calc = swe.calc_ut(jdut, p_id, flags)
            lon_val = calc[0][0] if isinstance(calc, tuple) and isinstance(calc[0], tuple) else (calc[0] if isinstance(calc, tuple) else 0.0)
            if name == "Rahu / Rahu": rahu_lon = lon_val
            if name == "Sun / Surya": sun_lon = lon_val
            
            # Check for retrograde (ignore Nodes & Luminaries)
            if name not in ["Sun / Surya", "Moon / Chandra", "Rahu / Rahu"]:
                is_retrograde = check_retrograde(jdut, p_id)
            
        sign_idx = int(lon_val / 30) % 12; sign_name = ZODIAC_SIGNS[sign_idx]
        _, nak_name = get_nakshatra_info(lon_val)
        
        # Append [R] flag for the PDF Renderer
        dig = get_planet_dignity(name, sign_name)
        if is_retrograde:
            dig += " [Retrograde]"

        # Calculate true circular angular difference (0 to 180 degrees)
        diff = abs(lon_val - sun_lon)
        angular_dist = min(diff, 360.0 - diff)
        
        positions[name] = {
            "sign": sign_name, "hindi_sign": HINDI_SIGNS[sign_name], "lon": lon_val % 360.0, 
            "nak": nak_name, "dignity": dig,
            "combust": (angular_dist < COMBUSTION_ORB.get(name, 0)) if name in COMBUSTION_ORB else False
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
            
    # --- PHASE 1 MATH INJECTIONS ---
    
    # 1. Neecha Bhanga Cancellation Check
    for p_name, p_data in positions.items():
        if check_neecha_bhanga(p_name, p_data, houses):
            positions[p_name]["dignity"] = "Neecha Bhanga (Cancelled Debilitation)"
            
    # 2. Extract Karakas (Soul/Spouse indicators)
    karakas = calculate_karakas(positions)

    # 3. Detect Karmic Doshas, Toxic Curses & Planetary Wars
    doshas = detect_structural_doshas(houses, positions)
    if check_kaal_sarp(houses):
        doshas.append("Kaal Sarp Dosha (All planets within Rahu-Ketu axis)")
    
    toxic_curses = detect_toxic_conjunctions(houses)
    doshas.extend(toxic_curses)
    
    # INJECT SPRINT 7: Graha Yuddha
    graha_yuddhas = detect_graha_yuddha(positions)
    doshas.extend(graha_yuddhas)

    # INJECT SPRINT 7: Panchanga Data (To stop Ayurvedic Hallucinations)
    moon_lon = positions["Moon / Chandra"]["lon"]
    panchanga_data = calculate_panchanga(jdut, sun_lon, moon_lon)

    vargas = calculate_vargas(positions, asc_lon)
    sav = calculate_full_sav(houses)
    yogas = detect_yogas(houses, positions)
    mahapurusha = detect_mahapurusha_yogas(houses, positions)
    yogas.extend(mahapurusha)

    # Send the new metrics to Groq LLM
    logic_summary = (
        f"[PANCHANGA]: {json.dumps(panchanga_data)}\n"
        f"[VARGAS]: {json.dumps(vargas)}\n"
        f"[SAV]: {json.dumps(sav)}\n"
        f"[YOGAS]: {json.dumps(yogas)}\n"
        f"[DOSHAS]: {json.dumps(doshas)}\n"
        f"[KARAKAS]: {json.dumps(karakas)}\n"
        f"[TRANSITS]: {calculate_transit_timings()}\n"
    )

    return asc_sign, positions, houses, sav, logic_summary, dt_local.isoformat()
  
def get_applicable_remedies(houses_dict, planet_data):
    remedies = []
    for p_name, p_data in planet_data.items():
        if p_data.get("combust") and f"{p_name}_Combust" in LAL_KITAB_DICT: remedies.append(f"{p_name} Combust: {LAL_KITAB_DICT[f'{p_name}_Combust']}")
        if p_data.get("dignity", "").startswith("Debilitated") and f"{p_name}_Debilitated" in LAL_KITAB_DICT: remedies.append(f"{p_name} Debilitated: {LAL_KITAB_DICT[f'{p_name}_Debilitated']}")
    for h_num, data in houses_dict.items():
        for p_name in data["occupants"]:
            if f"{p_name}_{h_num}" in LAL_KITAB_DICT: remedies.append(f"{p_name} in H{h_num}: {LAL_KITAB_DICT[f'{p_name}_{h_num}']}")
            
    # --- PHASE 1 WIRING: DOSHAS TO UPAYAS ---
    doshas = detect_structural_doshas(houses_dict, planet_data)
    if check_kaal_sarp(houses_dict): doshas.append("Kaal Sarp Dosha")
    
    toxic_curses = detect_toxic_conjunctions(houses_dict)
    doshas.extend(toxic_curses)
        
    for d in doshas:
        if "Mangalik" in d and "Mangalik Dosha" in LAL_KITAB_DICT: remedies.append(f"Mangalik Dosha: {LAL_KITAB_DICT['Mangalik Dosha']}")
        if "Sade Sati" in d and "Shani Sade Sati" in LAL_KITAB_DICT: remedies.append(f"Shani Sade Sati: {LAL_KITAB_DICT['Shani Sade Sati']}")
        if "Kemadruma" in d and "Kemadruma Yoga" in LAL_KITAB_DICT: remedies.append(f"Kemadruma Yoga: {LAL_KITAB_DICT['Kemadruma Yoga']}")
        if "Kaal Sarp" in d and "Kaal Sarp Dosha" in LAL_KITAB_DICT: remedies.append(f"Kaal Sarp Dosha: {LAL_KITAB_DICT['Kaal Sarp Dosha']}")
        if "Guru Chandal" in d: remedies.append("Guru Chandal Yoga: Donate yellow items to an orphanage. Apply a saffron tilak daily.")
        if "Grahan" in d: remedies.append("Grahan Yoga: Offer water to the Sun/Moon. Do not take major decisions during eclipses.")
        if "Vish" in d: remedies.append("Vish Yoga: Drink water from a silver vessel. Meditate on Shiva.")
        if "Angaraka" in d: remedies.append("Angaraka Yoga: Avoid aggressive arguments. Donate red lentils on Tuesday.")

    return list(dict.fromkeys(remedies))

# ==========================================
# PART 3: COGNITIVE ENGINE (Groq LLM API)
# (I will provide this block after Part 2)
# ==========================================
# ==========================================
# PART 3: COGNITIVE ENGINE (Groq LLM API)
# ==========================================

def call_groq_agent(system_prompt, user_prompt, models_list):
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        return json.dumps({"error": "GROQ_API_KEY environment variable is missing."})
        
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    
    # Safe payload without max_tokens overflow, leveraging native context buffer
    payload_base = {
        "messages": [
            {"role": "system", "content": system_prompt}, 
            {"role": "user", "content": user_prompt}
        ], 
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
    
    for model_name in models_list:
        payload = payload_base.copy()
        payload["model"] = model_name
        for attempt in range(2):
            try:
                res = requests.post(groq_url, headers=headers, json=payload, timeout=120)
                if res.status_code == 200: 
                    return res.json()['choices'][0]['message']['content']
                elif res.status_code == 429: 
                    time.sleep(15) 
                    continue
                else:
                    print(f"API Error {res.status_code} for {model_name}: {res.text}", flush=True)
                    break 
            except Exception as e: 
                print(f"Request Exception for {model_name}: {e}", flush=True)
                break
                
    return json.dumps({"error": "All AI models timed out, failed, or hit token ceilings."})

def generate_dialectic_insights(session_data, chat_id, send_message_func):
    MASTER_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
    base_cognitive_rules = """You are an Elite Executive Astrological Advisor.
    [DIALECTIC LAWS]
    1. OBJECTIVITY: Frame negative traits as 'Strategic Vulnerabilities' to be managed. Do not be overly fatalistic.
    2. THE PIVOT: Provide purely behavioral and psychological strategic advice in the 'executive_pivot'. DO NOT list physical rituals or remedies.
    3. FORMATTING: You MUST output a valid, raw JSON object. The text values inside the JSON must use HTML bullet points (<ul><li>) and bold tags (<b>) for scannability.
    4. DEPTH & LENGTH: Provide exactly 4 to 5 highly detailed, comprehensive, multi-layered bullet points per section. Ensure the analysis is deep, but you MUST safely close the JSON object."""

    base_user_msg = f"Ascendant: {session_data['asc_sign']}\nData: {session_data['logic_breakdown']}"

    swarm_chapters = {
        "psychology": base_cognitive_rules + "\nAnalyze the native's psychological operating system. Output JSON with EXACTLY these keys: 'asset', 'vulnerability', 'executive_pivot'.",
        "career_wealth": base_cognitive_rules + "\nAnalyze career apex and wealth potential. Output JSON with EXACTLY these keys: 'asset', 'vulnerability', 'executive_pivot'.",
        "relational_karma": base_cognitive_rules + "\nAnalyze relationship karma based on D-9 Navamsha. Output JSON with EXACTLY these keys: 'asset', 'vulnerability', 'executive_pivot'.",
        "ayurvedic_audit": base_cognitive_rules + "\nAnalyze the primary Ayurvedic Dosha. Output JSON with EXACTLY these keys: 'asset', 'vulnerability' (no medical claims), 'executive_pivot'.",
        "forecast": base_cognitive_rules + "\nAnalyze transits for the next 24 months. Output JSON with EXACTLY these keys: 'strategic_windows', 'structural_threats', 'executive_summary'."
    }

    eng_data = {}
    for chapter_key, system_prompt in swarm_chapters.items():
        send_message_func(chat_id, f"🧠 Synthesizing: {chapter_key.replace('_', ' ').title()}...")
        
        raw_res = call_groq_agent(system_prompt, base_user_msg, MASTER_MODELS).strip()
        
        match = re.search(r'\{.*\}', raw_res, re.DOTALL)
        clean_json = match.group(0) if match else raw_res
        
        try:
            parsed_data = json.loads(clean_json)
            
            if "error" in parsed_data:
                raise ValueError(parsed_data["error"])
                
            if chapter_key == "forecast" and "strategic_windows" not in parsed_data:
                raise ValueError("Keys missing in Forecast.")
            elif chapter_key != "forecast" and "asset" not in parsed_data:
                raise ValueError("Keys missing in Standard Chapter.")
                
            eng_data[chapter_key] = parsed_data
            
        except Exception as e:
            print(f"Data parsing exception for {chapter_key}: {e}", flush=True)
            
            safe_error = str(e).replace('<', '&lt;').replace('>', '&gt;')
            error_html = f"<ul><li><b style='color:#A95D45;'>SYSTEM DIAGNOSTIC:</b> {safe_error}</li></ul>"
            
            if chapter_key == "forecast":
                eng_data[chapter_key] = {"strategic_windows": error_html, "structural_threats": error_html, "executive_summary": error_html}
            else:
                eng_data[chapter_key] = {"asset": error_html, "vulnerability": error_html, "executive_pivot": error_html}
                
        time.sleep(5)
        
    return eng_data

# ==========================================
# PART 4: UI RENDERER (SVGs & WeasyPrint PDF)
# ==========================================
from weasyprint import HTML

def get_sacred_svg_symbols():
    """Generates centered Om and Swastika sacred geometry for headers."""
    return """
    <svg viewBox="0 0 400 60" width="100%" height="100%">
        <!-- Left Swastika -->
        <g transform="translate(140, 15) scale(0.9)" stroke="#B68A3A" stroke-width="2.5" fill="none" stroke-linecap="round">
            <path d="M15,0 L15,30 M0,15 L30,15 M15,0 L30,0 M15,30 L0,30 M0,0 L0,15 M30,30 L30,15"/>
            <circle cx="7.5" cy="7.5" r="1.5" fill="#B68A3A" stroke="none"/>
            <circle cx="22.5" cy="7.5" r="1.5" fill="#B68A3A" stroke="none"/>
            <circle cx="7.5" cy="22.5" r="1.5" fill="#B68A3A" stroke="none"/>
            <circle cx="22.5" cy="22.5" r="1.5" fill="#B68A3A" stroke="none"/>
        </g>
        <!-- Center Om -->
        <text x="200" y="44" font-size="34" font-family="'Helvetica', sans-serif" fill="#B68A3A" text-anchor="middle">ॐ</text>
        <!-- Right Swastika -->
        <g transform="translate(230, 15) scale(0.9)" stroke="#B68A3A" stroke-width="2.5" fill="none" stroke-linecap="round">
            <path d="M15,0 L15,30 M0,15 L30,15 M15,0 L30,0 M15,30 L0,30 M0,0 L0,15 M30,30 L30,15"/>
            <circle cx="7.5" cy="7.5" r="1.5" fill="#B68A3A" stroke="none"/>
            <circle cx="22.5" cy="7.5" r="1.5" fill="#B68A3A" stroke="none"/>
            <circle cx="7.5" cy="22.5" r="1.5" fill="#B68A3A" stroke="none"/>
            <circle cx="22.5" cy="22.5" r="1.5" fill="#B68A3A" stroke="none"/>
        </g>
    </svg>
    """

def generate_cover_page_svg(native_name="Confidential Dossier", birth_str=""):
    sacred_symbols = get_sacred_svg_symbols()
    return f"""
    <svg viewBox="0 0 800 1130" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: 100vh; font-family: 'Cinzel', serif;">
        <rect width="800" height="1130" fill="#0b111a" />
        <rect x="40" y="40" width="720" height="1050" fill="none" stroke="#B68A3A" stroke-width="1" opacity="0.5"/>
        <circle cx="400" cy="565" r="300" fill="none" stroke="#B68A3A" stroke-width="0.3" stroke-dasharray="2,6" opacity="0.3"/>
        <circle cx="400" cy="565" r="280" fill="none" stroke="#B68A3A" stroke-width="0.2" opacity="0.2"/>
        
        <g transform="translate(0, -50)">{sacred_symbols}</g>
        
        <text x="400" y="420" font-size="22" fill="#F9F8F6" text-anchor="middle" font-weight="300" letter-spacing="6">THE CELESTIAL STRATEGY</text>
        <text x="400" y="490" font-size="54" fill="#B68A3A" text-anchor="middle" font-weight="bold" letter-spacing="8">DOSSIER</text>
        
        <line x1="320" y1="540" x2="480" y2="540" stroke="#B68A3A" stroke-width="1" opacity="0.8"/>
        <text x="400" y="580" font-size="10" fill="#71866B" text-anchor="middle" letter-spacing="3" font-family="'Montserrat', sans-serif;">EXECUTIVE ARCHITECTURE • TACTICAL TIMING</text>
        
        <text x="400" y="800" font-size="10" fill="#F9F8F6" text-anchor="middle" letter-spacing="2" font-family="'Montserrat', sans-serif;" opacity="0.6">DOSSIER ID // CLEARANCE: EYES ONLY</text>
        <text x="400" y="830" font-size="20" fill="#B68A3A" text-anchor="middle" font-weight="bold" letter-spacing="3">{native_name}</text>
        <text x="400" y="860" font-size="11" fill="#71866B" text-anchor="middle" font-family="'Montserrat', sans-serif;">{birth_str}</text>
    </svg>
    """

def generate_vedic_chart_svg(chart_title, asc_sign, sign_to_planets_dict):
    width = 400; height = 400
    asc_idx = ZODIAC_SIGNS.index(asc_sign)
    h_coords = {
        1: (200, 100), 2: (100, 50), 3: (50, 100), 4: (100, 200),
        5: (50, 300), 6: (100, 350), 7: (200, 300), 8: (300, 350),
        9: (350, 300), 10: (300, 200), 11: (350, 100), 12: (300, 50)
    }
    
    # Map to Unicode symbols for a premium look
    glyph_map = {
        "Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿",
        "Jupiter": "♃", "Venus": "♀", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋", "Ascendant": "ASC"
    }
    
    house_planets = {i: [] for i in range(1, 13)}
    for sign_name, planets in sign_to_planets_dict.items():
        if sign_name in ZODIAC_SIGNS:
            sign_idx = ZODIAC_SIGNS.index(sign_name)
            h_num = ((sign_idx - asc_idx + 12) % 12) + 1
            for p in planets:
                p_base = p.split("/")[0].strip()
                house_planets[h_num].append(glyph_map.get(p_base, p_base[:2]))
                
    svg = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; font-family: \'Cinzel\', serif;">',
        '<rect x="0" y="0" width="400" height="400" fill="#F9F8F6" stroke="#B68A3A" stroke-width="1.5"/>',
        '<polygon points="200,0 400,200 200,400 0,200" fill="none" stroke="#B68A3A" stroke-width="1" opacity="0.7"/>',
        '<line x1="0" y1="0" x2="400" y2="400" stroke="#B68A3A" stroke-width="0.8" opacity="0.7"/>',
        '<line x1="400" y1="0" x2="0" y2="400" stroke="#B68A3A" stroke-width="0.8" opacity="0.7"/>',
        '<line x1="0" y1="200" x2="400" y2="200" stroke="#B68A3A" stroke-width="0.8" opacity="0.7"/>',
        '<line x1="200" y1="0" x2="200" y2="400" stroke="#B68A3A" stroke-width="0.8" opacity="0.7"/>',
        f'<text x="200" y="25" font-size="14" font-weight="bold" fill="#0b111a" text-anchor="middle" letter-spacing="1">{chart_title}</text>'
    ]
    for h_num, (x, y) in h_coords.items():
        sign_num = ((asc_idx + h_num - 1) % 12) + 1
        svg.append(f'<text x="{x}" y="{y-18}" font-size="10" fill="#71866B" text-anchor="middle" opacity="0.8">{sign_num}</text>')
        if house_planets[h_num]:
            svg.append(f'<text x="{x}" y="{y+8}" font-size="16" font-family="sans-serif" font-weight="bold" fill="#0b111a" text-anchor="middle">{ " ".join(house_planets[h_num]) }</text>')
    svg.append('</svg>')
    return "\n".join(svg)

def generate_sav_heatmap_svg(sav_dict):
    width = 600; height = 200; margin_top = 20; margin_bottom = 40
    chart_height = height - margin_top - margin_bottom; y_scale = chart_height / 50 
    baseline_y = height - margin_bottom - (28 * y_scale)
    
    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; font-family: \'Montserrat\', sans-serif;">',
        '<rect width="100%" height="100%" fill="#F9F8F6" rx="4" stroke="#e0e0e0" stroke-width="1" />',
        f'<line x1="20" y1="{baseline_y:.2f}" x2="{width-20}" y2="{baseline_y:.2f}" stroke="#A95D45" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.8"/>',
        f'<text x="{width-25}" y="{baseline_y-8:.2f}" font-size="10" fill="#A95D45" text-anchor="end" font-weight="bold">Karmic Baseline (28)</text>'
    ]
    for i in range(1, 13):
        score = sav_dict.get(i, 0)
        bar_height = max(0, min(score, 50)) * y_scale
        x = 35 + ((i - 1) * 45); y = height - margin_bottom - bar_height
        color = "#B68A3A" if score >= 28 else "#71866B"
        svg_parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="30" height="{bar_height:.2f}" fill="{color}" rx="3" ry="3" opacity="0.9"/>')
        svg_parts.append(f'<text x="{x + 15:.2f}" y="{y - 6:.2f}" font-size="11" font-weight="bold" fill="#0b111a" text-anchor="middle">{score}</text>')
        svg_parts.append(f'<text x="{x + 15:.2f}" y="{height - margin_bottom + 20}" font-size="11" fill="#58708C" text-anchor="middle">H{i}</text>')
    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

def build_infographic_module(data_dict, is_forecast=False):
    if is_forecast:
        return f"""
        <div class="info-content">
            <h4 class="green-heading">STRATEGIC WINDOWS</h4>
            {data_dict.get('strategic_windows', '')}
        </div>
        <div class="info-content">
            <h4 class="red-heading">STRUCTURAL THREATS</h4>
            {data_dict.get('structural_threats', '')}
        </div>
        <div class="pivot-quote">
            <h4 class="gold-heading">EXECUTIVE SUMMARY</h4>
            {data_dict.get('executive_summary', '')}
        </div>"""
    else:
        return f"""
        <div class="info-content">
            <h4 class="green-heading">STRATEGIC ASSETS</h4>
            {data_dict.get('asset', '')}
        </div>
        <div class="info-content">
            <h4 class="red-heading">STRUCTURAL VULNERABILITIES</h4>
            {data_dict.get('vulnerability', '')}
        </div>
        <div class="pivot-quote">
            <h4 class="gold-heading">EXECUTIVE PIVOT</h4>
            {data_dict.get('executive_pivot', '')}
        </div>"""

def build_and_render_pdf(session_data, eng_data, timeline_data, pdf_path):
    cover_svg = generate_cover_page_svg(native_name="CONFIDENTIAL DOSSIER", birth_str=session_data.get("birth_str", "").upper())
    sacred_header = f'<div class="sacred-header"><svg height="45" width="160" viewBox="0 0 400 60">{get_sacred_svg_symbols()}</svg></div>'

    # 1. Prepare D-1 Data
    d1_signs = {sign: [] for sign in ZODIAC_SIGNS}
    for p, d in session_data['planet_data'].items():
        d1_signs[d["sign"]].append(p)
    rasi_svg = generate_vedic_chart_svg("D-1 RASI (NATAL)", session_data['asc_sign'], d1_signs)

    # 2. Prepare D-9 Data
    d9_signs = {sign: [] for sign in ZODIAC_SIGNS}
    d9_asc = session_data.get('vargas', {}).get("Ascendant / Lagna", {}).get("D9", "Aries")
    for p, d in session_data.get('vargas', {}).items():
        if p != "Ascendant / Lagna": d9_signs[d["D9"]].append(p)
    navamsha_svg = generate_vedic_chart_svg("D-9 NAVAMSHA (RELATIONAL)", d9_asc, d9_signs)

    # 3. Prepare D-10 Data
    d10_signs = {sign: [] for sign in ZODIAC_SIGNS}
    d10_asc = session_data.get('vargas', {}).get("Ascendant / Lagna", {}).get("D10", "Aries")
    for p, d in session_data.get('vargas', {}).items():
        if p != "Ascendant / Lagna": d10_signs[d["D10"]].append(p)
    dashamsha_svg = generate_vedic_chart_svg("D-10 DASHAMSHA (CAREER)", d10_asc, d10_signs)

    sav_svg = generate_sav_heatmap_svg(session_data['sav'])

    eph_rows = ""
    for p_name, data in session_data['planet_data'].items():
        deg = f"{int(data['lon'] % 30)}° {int((data['lon'] % 1) * 60)}'"
        dignity_str = data['dignity']
        is_retro = "[Retrograde]" in dignity_str
        if is_retro: dignity_str = dignity_str.replace(" [Retrograde]", "")
        cond = [dignity_str.split('/')[0].strip()] if "/" in dignity_str else ([dignity_str] if dignity_str != "Neutral" else [])
        if is_retro: cond.append("Retrograde")
        if data.get('combust'): cond.append("Combust")
        eph_rows += f"<tr><td><strong>{p_name}</strong></td><td>{data['sign']}</td><td>{deg}</td><td>{data['nak']}</td><td>{','.join(cond) or 'Neutral'}</td></tr>"
    
    dasha_rows = "".join([f"<tr><td><strong>{r[0]}</strong></td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>" for r in timeline_data])
    
    mantra_rows = ""
    targets = set([{"Aries": "Mars / Mangal", "Taurus": "Venus / Shukra", "Gemini": "Mercury / Budh", "Cancer": "Moon / Chandra", "Leo": "Sun / Surya", "Virgo": "Mercury / Budh", "Libra": "Venus / Shukra", "Scorpio": "Mars / Mangal", "Sagittarius": "Jupiter / Guru", "Capricorn": "Saturn / Shani", "Aquarius": "Saturn / Shani", "Pisces": "Jupiter / Guru"}.get(session_data['asc_sign'])])
    for p, d in session_data['planet_data'].items():
        if d.get('combust') or d.get('dignity', '').startswith('Debilitated') or 'Rahu' in p or 'Ketu' in p: targets.add(p)
    for p in [t for t in targets if t and t in VEDIC_MANTRAS]:
        mantra_rows += f"<tr><td><strong>{p}</strong></td><td><em>{VEDIC_MANTRAS[p]}</em></td><td>{VEDIC_UPAYAS[p]}</td></tr>"

    lk_rows = ""
    for r in session_data.get('remedies', []):
        parts = r.split(':')
        if len(parts) == 2: lk_rows += f"<tr><td><strong>{parts[0].strip()}</strong></td><td>{parts[1].strip()}</td><td style='text-align:center;'><div class='checkbox'></div></td></tr>"
    if not lk_rows: lk_rows = '<tr><td colspan="3">No major structural Lal Kitab afflictions detected.</td></tr>'

    html_body = f"""
    <div class="cover-page">{cover_svg}</div>
    {sacred_header}
    
    <div class="content">
        <h2 class="section-title">01 — The Planetary Matrix</h2>
        <div class="synopsis" style="margin-bottom: 25px;">The D-1 Rasi chart is the fundamental geometric blueprint of the heavens at the moment of birth, dictating physical manifestation and core identity.</div>
        
        <div class="grid-2col">
            <div class="chart-box">{rasi_svg}</div>
            <div class="chart-box">
                <table class="data-table" style="margin-top:0;"><tr><th>Planet</th><th>Sign</th><th>Degree</th><th>Nakshatra</th><th>Condition</th></tr>{eph_rows}</table>
            </div>
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">02 — Inner Operating System</h2>
        <div class="synopsis" style="margin-bottom: 25px;">A cognitive teardown of psychological drivers, inherent assets, and subconscious friction points based on Ascendant and Moon geometries.</div>
        {build_infographic_module(eng_data.get('psychology', {}))}

        <div class="page-break"></div>
        <h2 class="section-title">03 — Career & Wealth Canvas</h2>
        <div class="synopsis" style="margin-bottom: 25px;">Analysis driven by the D-10 Dashamsha (Career Apex) chart and the Ashtakavarga Karmic Heatmap to identify wealth generation and structural limits.</div>
        
        <div class="grid-2col">
            <div>{build_infographic_module(eng_data.get('career_wealth', {}))}</div>
            <div class="chart-box">{dashamsha_svg}</div>
        </div>
        
        <h3 class="sub-title" style="margin-top: 30px;">Sarvashtakavarga (SAV) Karmic Heatmap</h3>
        <div class="sav-box">{sav_svg}</div>

        <div class="page-break"></div>
        <h2 class="section-title">04 — Relational Dynamics</h2>
        <div class="synopsis" style="margin-bottom: 25px;">Insights derived from the D-9 Navamsha chart, mapping the soul's trajectory in partnerships, marriage, and deep emotional contracts.</div>
        
        <div class="grid-2col">
            <div class="chart-box">{navamsha_svg}</div>
            <div>{build_infographic_module(eng_data.get('relational_karma', {}))}</div>
        </div>

        <div class="page-break"></div>
        <h2 class="section-title">05 — Tactical Forecast</h2>
        <div class="synopsis" style="margin-bottom: 25px;">A 24-month forward-looking radar plotting Vimshottari planetary periods against slow-moving macro transits to identify strategic action windows.</div>
        
        <h3 class="sub-title">Vimshottari Timeline</h3>
        <table class="data-table"><tr><th>Phase</th><th>Ruling Lords</th><th>Start Date</th><th>End Date</th></tr>{dasha_rows}</table>
        <div style="margin-top:20px;">{build_infographic_module(eng_data.get('forecast', {}), is_forecast=True)}</div>

        <div class="page-break"></div>
        <h2 class="section-title">06 — Ayurvedic & Vitality Reflection</h2>
        <div class="synopsis" style="margin-bottom: 25px;">An audit of physiological tendencies and energy management requirements to sustain high-level execution without burnout.</div>
        <div style="margin-top:20px;">{build_infographic_module(eng_data.get('ayurvedic_audit', {}))}</div>

        <div class="page-break"></div>
        <h2 class="section-title">07 — Holistic Remediation Planner</h2>
        <div class="synopsis" style="margin-bottom: 25px;">A synthesis of traditional spiritual technologies (Mantras) and behavioral protocols (Lal Kitab) designed to neutralize structural vulnerabilities.</div>
        
        <h3 class="sub-title">I. Vedic Mantras & Spiritual Upayas</h3>
        <table class="data-table"><tr><th>Target Energy</th><th>Vedic Beej Mantra (Chant 108x)</th><th>Traditional Protocol</th></tr>{mantra_rows}</table>
        
        <h3 class="sub-title" style="margin-top: 30px;">II. Lal Kitab Behavioral Protocols</h3>
        <table class="data-table"><tr><th>Karmic Friction</th><th>Actionable Behavioral Protocol</th><th style="width: 50px; text-align:center;">Done</th></tr>{lk_rows}</table>
    </div>
    """

    css = """
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Montserrat:wght@300;400;600&display=swap');
    
    @page { 
        size: letter; 
        margin: 2cm; 
        margin-top: 3.5cm;
        @top-center { content: element(sacred-header); }
        @bottom-right { content: counter(page); font-family: 'Montserrat', sans-serif; font-size: 8pt; color: #B68A3A; font-weight: bold; }
    }
    
    body { font-family: 'Montserrat', sans-serif; font-size: 9.5pt; line-height: 1.7; color: #101827; background-color: #F9F8F6; margin: 0; padding: 0; }
    
    .cover-page { height: 100vh; margin-top: -3.5cm; margin-left: -2cm; margin-right: -2cm; background-color: #0b111a; }
    
    .sacred-header { position: running(sacred-header); text-align: center; margin-top: 0.5cm; }
    
    .page-break { page-break-before: always; }
    
    h1, h2.section-title { font-family: 'Cinzel', serif; color: #0b111a; font-size: 16pt; font-weight: 700; letter-spacing: 2px; border-bottom: 1px solid #B68A3A; padding-bottom: 8px; margin-bottom: 15px; }
    h3.sub-title { font-family: 'Cinzel', serif; color: #B68A3A; font-size: 12pt; font-weight: 700; letter-spacing: 1.5px; margin-top: 20px; margin-bottom: 12px; }
    
    .grid-2col { display: block; width: 100%; clear: both; overflow: hidden; margin-bottom: 20px; }
    .grid-2col > div { float: left; width: 48%; box-sizing: border-box; }
    .grid-2col > div:last-child { float: right; }
    
    .info-content { margin-bottom: 15px; }
    .info-content h4 { margin: 0 0 8px 0; font-family: 'Montserrat', sans-serif; font-size: 9pt; font-weight: 600; letter-spacing: 1.5px; }
    .green-heading { color: #71866B; }
    .red-heading { color: #A95D45; }
    .gold-heading { color: #B68A3A; }
    
    .info-content ul { margin: 0; padding-left: 20px; list-style-type: none; }
    .info-content li { margin-bottom: 8px; position: relative; }
    .info-content li::before { content: "◆"; color: #B68A3A; font-size: 8pt; position: absolute; left: -15px; top: 2px; }
    
    .pivot-quote { background-color: #ffffff; border-left: 4px solid #B68A3A; padding: 15px 20px; margin: 20px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }
    .pivot-quote ul { padding-left: 20px; margin: 0; }
    .pivot-quote li { margin-bottom: 8px; }
    
    .synopsis { font-size: 9pt; color: #58708C; font-style: italic; border-left: 2px solid #58708C; padding-left: 12px; line-height: 1.5; }
    
    table.data-table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 8.5pt; font-family: 'Montserrat', sans-serif; }
    table.data-table th { color: #58708C; font-weight: 600; padding: 8px 5px; text-align: left; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #B68A3A; }
    table.data-table td { padding: 10px 5px; border-bottom: 1px solid #e0e0e0; vertical-align: middle; }
    
    .checkbox { width:14px; height:14px; border:1.5px solid #101827; margin:auto; border-radius: 2px; }
    
    .chart-box { text-align: center; }
    .sav-box { text-align: center; margin-bottom: 15px; }
    """
    try:
        HTML(string=f"<html><head><style>{css}</style></head><body>{html_body}</body></html>").write_pdf(pdf_path)
        return True
    except Exception as e:
        print(f"PDF ERROR: {e}")
        return False
        
# ==========================================
# PART 5: THE ORCHESTRATOR (Flask, Webhook, Threads)
# (I will provide this final block after Part 4)
# ==========================================
# ==========================================
# PART 5: THE ORCHESTRATOR (Flask, Webhook, Threads)
# ==========================================

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    chat_id INTEGER PRIMARY KEY, 
                    state TEXT, 
                    name TEXT, 
                    dob TEXT, 
                    tob TEXT, 
                    pob TEXT, 
                    lat REAL, 
                    lon REAL
                )''')
    conn.commit()
    conn.close()

init_db()

def send_telegram_message(chat_id, text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token: 
        print(f"Telegram Token Missing. Message to {chat_id}: {text}")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def send_telegram_document(chat_id, pdf_path):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token: return
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(pdf_path, 'rb') as f:
        requests.post(url, data={"chat_id": chat_id}, files={"document": f})

def background_generation_worker(chat_id, name, day, month, year, hour, minute, lat, lon, birth_str):
    try:
        send_telegram_message(chat_id, "✨ Calculating precise planetary geometry and Ephemeris...")
        asc_sign, positions, houses, sav, logic_summary, dt_iso = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
        remedies = get_applicable_remedies(houses, positions)
        
        session_data = {
            "asc_sign": asc_sign, "planet_data": positions, "houses": houses, 
            "sav": sav, "logic_breakdown": logic_summary, "remedies": remedies, "birth_str": birth_str
        }
        
        eng_data = generate_dialectic_insights(session_data, chat_id, send_message_func=send_telegram_message)
        
        send_telegram_message(chat_id, "📐 Compiling your SVG charts and rendering your Executive Dossier via WeasyPrint...")
        timeline = calculate_vimshottari_timeline(positions["Moon / Chandra"]["lon"], dt_iso)
        
        pdf_filename = f"Celestial_Strategy_{chat_id}.pdf"
        success = build_and_render_pdf(session_data, eng_data, timeline, pdf_filename)
        
        if success and os.path.exists(pdf_filename):
            send_telegram_document(chat_id, pdf_filename)
            send_telegram_message(chat_id, "🎯 Your Celestial Strategy Dossier is ready. Review your strategic assets and tactical roadmap.")
            os.remove(pdf_filename)
        else:
            send_telegram_message(chat_id, "❌ Critical PDF rendering error occurred. Please try again.")
            
    except Exception as e:
        print(f"Worker Exception: {e}", flush=True)
        send_telegram_message(chat_id, f"❌ System Error during dossier compilation: {str(e)}")
    
    finally:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE sessions SET state='IDLE' WHERE chat_id=?", (chat_id,))
        conn.commit()
        conn.close()

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data: return jsonify({"status": "ok"})
    
    chat_id = data['message']['chat']['id']
    text = data['message'].get('text', '').strip()
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT state, name, dob, tob, pob, lat, lon FROM sessions WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    state = row[0] if row else 'IDLE'
    
    if text == '/start':
        if row: c.execute("UPDATE sessions SET state='AWAIT_NAME' WHERE chat_id=?", (chat_id,))
        else: c.execute("INSERT OR REPLACE INTO sessions (chat_id, state) VALUES (?, 'AWAIT_NAME')", (chat_id,))
        conn.commit()
        conn.close()
        send_telegram_message(chat_id, "🏛️ Welcome to THE CELESTIAL STRATEGY DOSSIER.\nPlease enter your Full Name:")
        return jsonify({"status": "ok"})
        
    if state == 'AWAIT_NAME':
        c.execute("UPDATE sessions SET name=?, state='AWAIT_DOB' WHERE chat_id=?", (text, chat_id))
        conn.commit()
        conn.close()
        send_telegram_message(chat_id, "📅 Enter your Date of Birth (DD-MM-YYYY):")
        return jsonify({"status": "ok"})
        
    elif state == 'AWAIT_DOB':
        c.execute("UPDATE sessions SET dob=?, state='AWAIT_TOB' WHERE chat_id=?", (text, chat_id))
        conn.commit()
        conn.close()
        send_telegram_message(chat_id, "⏰ Enter your Exact Time of Birth in 24-hour format (HH:MM):")
        return jsonify({"status": "ok"})
        
    elif state == 'AWAIT_TOB':
        c.execute("UPDATE sessions SET tob=?, state='AWAIT_POB' WHERE chat_id=?", (text, chat_id))
        conn.commit()
        conn.close()
        send_telegram_message(chat_id, "📍 Enter your City & Country of Birth (e.g., New Delhi, India):")
        return jsonify({"status": "ok"})
        
    elif state == 'AWAIT_POB':
        name = row[1]; dob = row[2]; tob = row[3]; pob = text
        c.execute("UPDATE sessions SET pob=?, state='PROCESSING' WHERE chat_id=?", (pob, chat_id))
        conn.commit()
        conn.close()
        
        try:
            d_parts = dob.split('-'); day, month, year = int(d_parts[0]), int(d_parts[1]), int(d_parts[2])
            t_parts = tob.split(':'); hour, minute = int(t_parts[0]), int(t_parts[1])
            
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={pob}&count=1"
            geo_res = requests.get(geo_url).json()
            if not geo_res.get('results'):
                send_telegram_message(chat_id, "❌ Location not found. Please restart with /start and enter a valid city.")
                return jsonify({"status": "ok"})
                
            lat = geo_res['results'][0]['latitude']
            lon = geo_res['results'][0]['longitude']
            
            birth_str = f"{dob} at {tob} in {pob}"
            send_telegram_message(chat_id, f"🚀 Initializing synthesis for {name} ({birth_str})...")
            
            threading.Thread(target=background_generation_worker, args=(chat_id, name, day, month, year, hour, minute, lat, lon, birth_str)).start()
            
        except Exception as e:
            send_telegram_message(chat_id, f"❌ Input parsing error: {str(e)}. Please restart with /start.")
            
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/', methods=['GET'])
def index():
    return "Celestial Strategy Bot is running live.", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
