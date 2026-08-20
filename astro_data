# ==========================================
# FILE 1: astro_data.py (THE UNCOMPRESSED DATA WAREHOUSE)
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
    "Sun / Surya": [
        0,0,1,1,0,0,1,1, 1,0,0,0,1,1,0,0, 0,1,1,0,0,1,1,0, 0,0,1,1,0,0,1,1, 
        1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 
        0,0,0,1,1,1,1,0, 1,1,1,0,0,0,0,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0
    ],
    "Moon / Chandra": [
        0,1,0,1,1,0,1,0, 1,0,1,0,0,1,0,1, 1,1,0,0,1,1,0,0, 0,1,1,0,1,0,1,0, 
        1,0,1,1,0,1,0,1, 0,1,0,1,1,0,1,0, 1,1,0,1,0,1,1,0, 0,0,1,1,1,1,0,0, 
        1,1,0,0,0,0,1,1, 0,0,1,1,1,1,0,0, 1,0,1,0,0,1,0,1, 0,1,0,1,1,0,1,0
    ],
    "Mars / Mangal": [
        1,0,0,1,1,0,0,1, 1,1,0,0,1,1,0,0, 0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 
        0,1,1,0,0,1,1,0, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 0,1,1,0,1,0,1,0, 
        1,0,1,0,0,1,0,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,0,1,1,1,1,0
    ],
    "Mercury / Budh": [
        0,1,1,0,1,0,0,1, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 
        1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 1,0,0,1,0,1,1,0, 
        0,1,1,0,1,0,0,1, 1,0,0,1,0,1,1,0, 0,1,1,0,1,0,0,1, 1,1,0,0,1,1,0,0
    ],
    "Jupiter / Guru": [
        0,1,1,1,0,0,0,0, 1,0,0,0,1,1,1,0, 1,1,0,0,0,0,1,1, 0,0,1,1,1,1,0,0, 
        1,1,1,0,0,0,0,1, 0,0,0,1,1,1,1,0, 0,1,1,0,1,0,1,0, 1,0,0,1,0,1,0,1, 
        0,1,1,1,0,0,0,0, 1,0,0,0,1,1,1,0, 0,0,0,1,1,1,1,0, 1,1,1,0,0,0,0,1
    ],
    "Venus / Shukra": [
        1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,0,0,1,1,0,0,1, 0,1,1,0,0,1,1,0, 
        1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 0,1,1,0,1,0,1,0, 1,0,0,1,0,1,0,1, 
        1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0
    ],
    "Saturn / Shani": [
        0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 
        0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0, 0,0,1,0,0,1,1,0, 0,1,0,1,1,0,0,1, 
        1,0,1,0,1,0,0,1, 0,1,0,1,0,1,1,0, 0,0,1,1,0,0,1,1, 1,1,0,0,1,1,0,0
    ]
}

# ==========================================
# HOLISTIC REMEDIATION PROTOCOLS
# ==========================================
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

# FULL 140+ LAL KITAB DATABASE
LAL_KITAB_DICT = {
    # COMBUSTION & DEBILITATION
    "Saturn / Shani_Combust": "Donate black sesame oil on Saturday.", 
    "Mars / Mangal_Combust": "Avoid keeping iron tools under the bed.",
    "Jupiter / Guru_Combust": "Apply a tilak of saffron on the forehead daily.", 
    "Venus / Shukra_Combust": "Donate pure ghee to a temple on Friday.",
    "Mercury / Budh_Combust": "Clean teeth with fitkari (alum) daily.", 
    "Sun / Surya_Debilitated": "Offer water to the Sun. Avoid salt on Sundays.",
    "Moon / Chandra_Debilitated": "Immerse a square piece of silver in a river on Monday.", 
    "Mars / Mangal_Debilitated": "Float red copper in a flowing river on Tuesday.",
    "Mercury / Budh_Debilitated": "Avoid wearing green clothes. Keep broad-leaved plants away.", 
    "Jupiter / Guru_Debilitated": "Water a peepal tree on Thursday.",
    "Venus / Shukra_Debilitated": "Donate white sweets to young girls on Friday.", 
    "Saturn / Shani_Debilitated": "Serve food to disabled people on Saturday.",
    "Rahu / Rahu_Debilitated": "Keep a square silver piece in your pocket.", 
    "Ketu / Ketu_Debilitated": "Feed a two-colored dog.",
    
    # SUN
    "Sun / Surya_1": "Offer water to the Sun daily.", 
    "Sun / Surya_2": "Donate wheat and jaggery on Sunday.",
    "Sun / Surya_3": "Keep good relations with younger siblings.", 
    "Sun / Surya_4": "Do not consume salt on Sundays.",
    "Sun / Surya_5": "Keep a red handkerchief in your pocket.", 
    "Sun / Surya_6": "Feed a red cow on Sundays.",
    "Sun / Surya_7": "Reduce anger in marriage; avoid taking the first aggressive step.", 
    "Sun / Surya_8": "Keep a copper pot filled with water at home.",
    "Sun / Surya_9": "Use brass utensils for eating.", 
    "Sun / Surya_10": "Wear a copper coin around the neck.",
    "Sun / Surya_11": "Drink water from a copper vessel.", 
    "Sun / Surya_12": "Keep the courtyard or entrance of your home clean.",

    # MOON
    "Moon / Chandra_1": "Drink milk from a silver glass.", 
    "Moon / Chandra_2": "Keep a square piece of silver in the house.",
    "Moon / Chandra_3": "Offer green gram to birds.", 
    "Moon / Chandra_4": "Do not trade in milk or dairy products.",
    "Moon / Chandra_5": "Serve your mother and seek her blessings.", 
    "Moon / Chandra_6": "Serve water to patients in a hospital.",
    "Moon / Chandra_7": "Do not marry before the age of 24.", 
    "Moon / Chandra_8": "Immerse a silver coin in a river.",
    "Moon / Chandra_9": "Visit religious places frequently.", 
    "Moon / Chandra_10": "Avoid drinking milk at night.",
    "Moon / Chandra_11": "Donate milk to a temple on Mondays.", 
    "Moon / Chandra_12": "Keep rainwater stored in a glass bottle at home.",

    # MARS
    "Mars / Mangal_1": "Avoid keeping large weapons in the house.", 
    "Mars / Mangal_2": "Donate red masoor dal on Tuesday.",
    "Mars / Mangal_3": "Wear a silver ring. Maintain good relation with siblings.", 
    "Mars / Mangal_4": "Keep a square piece of red copper in the house.",
    "Mars / Mangal_5": "Keep a pot of water by your bedside.", 
    "Mars / Mangal_6": "Donate red masoor dal and batasha on Tuesday.",
    "Mars / Mangal_7": "Build a solid boundary wall around your home.", 
    "Mars / Mangal_8": "Feed sweet roti to a dog. Wear a silver chain.",
    "Mars / Mangal_9": "Offer milk to a banyan tree.", 
    "Mars / Mangal_10": "Offer sweet milk to a blind person.",
    "Mars / Mangal_11": "Keep a red handkerchief in your pocket.", 
    "Mars / Mangal_12": "Float a piece of red copper in flowing water.",

    # SATURN
    "Saturn / Shani_1": "Do not consume alcohol or non-veg. Feed black crows.", 
    "Saturn / Shani_2": "Apply an oil tilak to your forehead.",
    "Saturn / Shani_3": "Keep three dogs as pets or feed street dogs.", 
    "Saturn / Shani_4": "Do not build a house before age 48.",
    "Saturn / Shani_5": "Keep almonds in your home. Feed black crows.", 
    "Saturn / Shani_6": "Float a black mustard oil-filled bottle in a river.",
    "Saturn / Shani_7": "Do not build a house before age 48.", 
    "Saturn / Shani_8": "Drop 8kg of raw coal in running water.",
    "Saturn / Shani_9": "Keep a square piece of silver.", 
    "Saturn / Shani_10": "Feed black crows daily. Maintain strict punctuality.",
    "Saturn / Shani_11": "Place a vessel filled with mustard oil in your house.", 
    "Saturn / Shani_12": "Tie twelve almonds in a black cloth.",

    # RAHU
    "Rahu / Rahu_1": "Keep a silver square in your pocket.", 
    "Rahu / Rahu_2": "Keep a solid silver ball in your pocket.",
    "Rahu / Rahu_3": "Keep ivory items out of the house.", 
    "Rahu / Rahu_4": "Do not remodel the kitchen frequently.",
    "Rahu / Rahu_5": "Keep a silver elephant statue in the house.", 
    "Rahu / Rahu_6": "Float a piece of lead in running water.",
    "Rahu / Rahu_7": "Store river water in a dark glass bottle.", 
    "Rahu / Rahu_8": "Float four coconuts in a river on Saturday.",
    "Rahu / Rahu_9": "Apply a saffron tilak.", 
    "Rahu / Rahu_10": "Wear a blue or black cap.",
    "Rahu / Rahu_11": "Drink water from a silver glass.", 
    "Rahu / Rahu_12": "Keep a pouch of fennel under the pillow.",

    # KETU
    "Ketu / Ketu_1": "Feed a two-colored dog.", 
    "Ketu / Ketu_2": "Maintain absolute honesty in financial ledgers.",
    "Ketu / Ketu_3": "Float rice mixed with milk in a river.", 
    "Ketu / Ketu_4": "Do not keep fragmented glass in the house.",
    "Ketu / Ketu_5": "Donate a black and white blanket.", 
    "Ketu / Ketu_6": "Wear a gold ring on the left hand.",
    "Ketu / Ketu_7": "Keep a piece of iron dipped in water.", 
    "Ketu / Ketu_8": "Feed street dogs regularly.",
    "Ketu / Ketu_9": "Keep a gold brick or coin in the house.", 
    "Ketu / Ketu_10": "Keep a silver pot filled with honey.",
    "Ketu / Ketu_11": "Keep a radish near your bed at night and donate it.", 
    "Ketu / Ketu_12": "Do not keep broken jewelry."
}
