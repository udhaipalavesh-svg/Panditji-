@app.route('/', methods=['POST', 'GET'])
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Render Persistent Bot Server is Active", 200
        
    try:
        update = request.get_json(silent=True)
        if not update:
            return jsonify(status="ignored"), 200
            
        print(f"Received update: {update}", flush=True)

        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            user_text = update["message"]["text"].strip()
            
            if user_text.startswith("/start"):
                welcome_msg = "Welcome! Send your birth details to receive the comprehensive 8-part astrological report:\nDD-MM-YYYY HH:MM City\n(e.g., 02-01-1980 19:25 Chandigarh)"
                send_message(chat_id, welcome_msg)
            else:
                match = re.search(r'(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2})\s+(.+)', user_text)
                if not match:
                    send_message(chat_id, "Please use format: DD-MM-YYYY HH:MM City\n(e.g., 02-01-1980 19:25 Chandigarh)")
                    return jsonify(status="success"), 200
                    
                send_message(chat_id, "Executing high-precision Sidereal scan, computing Dasha timeline and generating 8-part master report...")
                
                day, month, year, hour, minute, city_input = match.groups()
                day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
                city_input = city_input.strip()

                lat, lon, city_clean = get_coordinates(city_input)
                asc_sign, asc_nak, asc_pada, planets, active_dasha = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
                
                os.makedirs("/tmp", exist_ok=True)
                file_tag = str(int(time.time()))
                svg_filename = f"natal_chart_{file_tag}"
                svg_path = f"/tmp/{svg_filename}.svg"

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
                        
                north.draw("/tmp/", svg_filename)
                send_document(chat_id, svg_path)

                planet_summary = "\n".join([f"- {p}: {info[0]} | Nakshatra: {info[2]} (Pada {info[3]})" for p, info in planets.items()])
                
                groq_key = os.environ.get("GROQ_API_KEY")
                today_date = datetime.now().strftime("%B %d, %Y")
                groq_url = "https://api.groq.com/openai/v1/chat/completions"
                
                prompt = f"""
[SYSTEM ROLE]
You are Panditji, an uncompromising master Vedic Astrologer. Today's date is {today_date}.

[INPUT DATA]
- Timing Engine (Vimshottari Dasha): {active_dasha}
- Ascendant (Lagna): {asc_sign} in {asc_nak} Pada {asc_pada}
- Planetary Array:
{planet_summary}

[OUTPUT DIRECTIVE]
Generate a high-precision, unyielding Vedic analysis. Use concise bullet points under each heading to eliminate fluff and maximize analytical density. Always include Hindi names in brackets for every planet (e.g., Saturn (Shani), Moon (Chandra)).

Structure the report strictly into these 8 sections:
1. **Star & Nakshatra Brief**: Core celestial alignment overview.
2. **Detailed Star Positions**: House-by-house breakdown of planetary strengths.
3. **Cosmic Conflicts**: Active planetary oppositions, conjunctions, or afflictions.
4. **General Life Prediction**: Broad trajectory across career, wealth, and life path.
5. **Detailed Manifestations**: Granular temporal predictions.
6. **Karmic Liabilities & Confinement (Bandhana Yoga)**: Rigorous evaluation of 6th/8th/12th houses, litigation weights, and restriction indicators.
7. **Corrective Remedies**: Exhaustive Lal Kitab & Vedic remedial measures.
8. **Rare Yogas & Anomalies**: Unique structural configurations present in the chart.
"""

                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {groq_key}"
                }

                res = requests.post(groq_url, headers=headers, json=payload, timeout=90)
                if res.status_code == 200:
                    data = res.json()
                    final_text = data['choices'][0]['message']['content']
                    send_message(chat_id, final_text)
                else:
                    send_message(chat_id, f"Groq API Error HTTP {res.status_code}: {res.text[:150]}")

    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        
    return jsonify(status="success"), 200
    
