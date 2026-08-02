                planet_summary = "\n".join([f"- {p}: {info[0]} | Nakshatra: {info[2]} (Pada {info[3]})" for p, info in planets.items()])
                
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={gemini_key}"

                # --- PART 1: Sections 1 to 4 ---
                prompt_part1 = f"""
                You are Panditji, an uncompromising master Vedic Astrologer. Today's date is {today_date}.
                Active Timing Engine (Vimshottari Dasha): {active_dasha}
                
                Sidereal Lahiri Chart Data:
                - Ascendant (Lagna): {asc_sign} in {asc_nak} Pada {asc_pada}
                {planet_summary}
                
                Deliver ONLY sections 1 through 4 with high analytical depth:
                1. Star and Nakshatra Position in Brief
                2. Star and Nakshatra Positions in Detail
                3. Conflicts Amongst Stars and Nakshatras
                4. General Prediction
                
                Rule: Mention Hindi names in brackets for every planet.
                """
                
                res1 = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt_part1}]}]})
                if res1.status_code == 200:
                    text_part1 = res1.json()['candidates'][0]['content']['parts'][0]['text']
                    send_message(chat_id, text_part1)

                # --- PART 2: Sections 5 to 8 ---
                prompt_part2 = f"""
                You are Panditji, an uncompromising master Vedic Astrologer. Today's date is {today_date}.
                Active Timing Engine (Vimshottari Dasha): {active_dasha}
                
                Sidereal Lahiri Chart Data:
                - Ascendant (Lagna): {asc_sign} in {asc_nak} Pada {asc_pada}
                {planet_summary}
                
                Deliver ONLY sections 5 through 8 with high analytical depth, explicitly covering Bandhana Yoga, litigation weights, psychological impacts, and Lal Kitab remedies:
                5. Prediction in Detail
                6. Potential Issues, Psychological Impact, and Legal/Confinement Deductions
                7. Remedies (Exhaustive Lal Kitab & Vedic Corrective Actions)
                8. Extraordinary Cosmic Anomalies & Rare Yogas
                
                Rule: Mention Hindi names in brackets for every planet.
                """
                
                res2 = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt_part2}]}]})
                if res2.status_code == 200:
                    text_part2 = res2.json()['candidates'][0]['content']['parts'][0]['text']
                    send_message(chat_id, text_part2)
                    
