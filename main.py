@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Render Persistent Bot Server is Active", 200
        
    try:
        update = request.get_json(silent=True)
        if not update:
            return jsonify(status="ignored"), 200
            
        gemini_key = os.environ.get("GEMINI_API_KEY")
        today_date = datetime.now().strftime("%B %d, %Y")

        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"]
            
            if user_text.startswith("/start"):
                welcome_msg = "Welcome! Send your birth details to receive the comprehensive 8-part astrological report:\nDD-MM-YYYY HH:MM City\n(e.g., 02-01-1980 19:25 Chandigarh)"
                send_message(chat_id, welcome_msg)
            else:
                send_message(chat_id, "Executing high-precision Sidereal scan, computing Dasha timeline and generating 8-part master report...")

                match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})\s+(.+)', user_text)
                if not match:
                    send_message(chat_id, "Please use format: DD-MM-YYYY HH:MM City\n(e.g., 02-01-1980 19:25 Chandigarh)")
                    return jsonify(status="success"), 200
                    
                day, month, year, hour, minute, city_input = match.groups()
                day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                city_input = city_input.strip()

                lat, lon, city_clean = get_coordinates(city_input)
                asc_sign, asc_nak, asc_pada, planets, active_dasha = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                
                # Generate Chart SVG
                north = chart.NorthChart("Natal Chart (Lahiri)", f"{day:02d}-{month:02d}-{year} ({city_clean})", IsFullChart=True)
                north.set_ascendantsign(asc_sign)
                
                p_map = {
                    "Sun (Surya)": chart.SUN, "Moon (Chandra)": chart.MOON,
                    "Mars (Mangal)": chart.MARS, "Mercury (Budh)": chart.MERCURY,
                    "Jupiter (Guru)": chart.JUPITER, "Venus (Shukra)": chart.VENUS,
                    "Saturn (Shani)": chart.SATURN, "Rahu": chart.RAHU, "Ketu": chart.KETU
                }
                for p_name, p_code in p_map.items():
                    if p_name in planets:
                        sign_name, _, _, _ = planets[p_name]
                        sign_idx = ZODIAC_SIGNS.index(sign_name) + 1
                        north.add_planet(p_code, p_name[:2], sign_idx)
                        
                os.makedirs("/tmp", exist_ok=True)
                svg_path = "/tmp/natal_chart.svg"
                north.draw("/tmp/", "natal_chart")
                send_document(chat_id, svg_path)

                planet_summary = "\n".join([f"- {p}: {info[0]} | Nakshatra: {info[2]} (Pada {info[3]})" for p, info in planets.items()])
                
                prompt = f"""
                You are Panditji, an uncompromising master Vedic Astrologer. Today's date is {today_date}.
                Active Timing Engine (Vimshottari Dasha): {active_dasha}
                
                Sidereal Lahiri Chart Data:
                - Ascendant (Lagna): {asc_sign} in {asc_nak} Pada {asc_pada}
                {planet_summary}
                
                MANDATORY INSTRUCTIONS:
                - Deliver an exhaustive, highly rigorous analytical report structured into these exact 8 headings:
                  1. Star and Nakshatra Position in Brief
                  2. Star and Nakshatra Positions in Detail
                  3. Conflicts Amongst Stars and Nakshatras
                  4. General Prediction
                  5. Prediction in Detail
                  6. Potential Issues, Psychological Impact, and Legal/Confinement Deductions (explicitly analyze Bandhana Yoga, 6th/8th/12th house weights, and prison/litigation reality if present)
                  7. Remedies (Exhaustive Lal Kitab & Vedic Corrective Actions)
                  8. Extraordinary Cosmic Anomalies & Rare Yogas
                - Rule: Mention Hindi names in brackets for every planet (e.g., Saturn (Shani), Moon (Chandra)). Keep the tone sharp, professional, and uncompromising.
                """

                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"
                res = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt}]}]})
                
                if res.status_code == 200:
                    final_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                    send_message(chat_id, final_text)
                else:
                    send_message(chat_id, "The celestial connection flickered. Please resend your birth details.")

    except Exception as e:
        print(f"Error: {str(e)}")
        
    return jsonify(status="success"), 200
    
