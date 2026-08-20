# ==========================================
# PART 2: astro_math.py (MATH & PHYSICS ENGINE)
# ==========================================
import swisseph as swe
from datetime import datetime, timedelta
import json
from astro_data import *

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

def get_applicable_remedies(houses_dict, planet_data):
    remedies = []
    for p_name, p_data in planet_data.items():
        if p_data.get("combust") and f"{p_name}_Combust" in LAL_KITAB_DICT: remedies.append(f"{p_name} Combust: {LAL_KITAB_DICT[f'{p_name}_Combust']}")
        if p_data.get("dignity", "").startswith("Debilitated") and f"{p_name}_Debilitated" in LAL_KITAB_DICT: remedies.append(f"{p_name} Debilitated: {LAL_KITAB_DICT[f'{p_name}_Debilitated']}")
    for h_num, data in houses_dict.items():
        for p_name in data["occupants"]:
            if f"{p_name}_{h_num}" in LAL_KITAB_DICT: remedies.append(f"{p_name} in H{h_num}: {LAL_KITAB_DICT[f'{p_name}_{h_num}']}")
    return list(dict.fromkeys(remedies))
