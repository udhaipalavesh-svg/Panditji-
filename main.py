import os
import re
import json
import time
import threading
import sqlite3
import requests
import markdown
import swisseph as swe
from flask import Flask, request, jsonify
from weasyprint import HTML

# ==========================================
# 1. INITIALIZATION & CONFIGURATION
# ==========================================
app = Flask(__name__)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Universally Stable Groq Models (Bypassing the API Tier Errors)
MODEL_MASTER_AGENT = "llama3-70b-8192"
MODEL_TRANSLATOR = "mixtral-8x7b-32768"
MODEL_QA = "llama3-8b-8192"

DB_FILE = "astro_sessions.db"

# ==========================================
# 2. SQLITE SESSION MANAGER
# ==========================================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS sessions (
                            chat_id TEXT PRIMARY KEY,
                            data TEXT
                        )''')

def get_session(chat_id):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.execute("SELECT data FROM sessions WHERE chat_id = ?", (str(chat_id),))
        row = cur.fetchone()
        return json.loads(row[0]) if row else None

def save_session(chat_id, data):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT OR REPLACE INTO sessions (chat_id, data) VALUES (?, ?)", 
                     (str(chat_id), json.dumps(data)))

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def send_document(chat_id, file_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, 'rb') as f:
        requests.post(url, data={"chat_id": chat_id}, files={"document": f})

def safe_get(data, keys, default="*Data Unavailable*"):
    """Recursively fetches keys from JSON safely to prevent KeyErrors."""
    current = data
    try:
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current if current else default
    except Exception:
        return default

def md_to_html(text):
    """Safely converts markdown strings to HTML."""
    if not isinstance(text, str):
        text = str(text)
    return markdown.markdown(text)

def generate_pdf_weasyprint(html_string, output_path):
    try:
        HTML(string=html_string).write_pdf(output_path)
        return True
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        return False

# ==========================================
# 4. SWISS EPHEMERIS MATH ENGINE
# ==========================================
def calculate_chart_logic(user_text):
    """
    Parses user input, fetches coordinates, and calculates exact 
    Vedic Sidereal planetary positions using Swiss Ephemeris.
    """
    try:
        match = re.search(r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{4})\s+(\d{1,2})[:.](\d{2})\s+([A-Za-z\s]+)', user_text)
        if not match:
            return "Error: Could not parse birth details."
        
        day, month, year, hour, minute, city = match.groups()
        day, month, year, hour, minute = int(day), int(month), int(year), int(hour), int(minute)
        
        url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
        try:
            res = requests.get(url, headers={'User-Agent': 'AstroBot/1.0'}, timeout=5).json()
            lat, lon = float(res[0]['lat']), float(res[0]['lon'])
        except:
            lat, lon = 28.6139, 77.2090 # Default to Delhi

        swe.set_sid_mode(swe.SIDM_LAHIRI)
        jd = swe.julday(year, month, day, hour + (minute / 60.0) - 5.5)
        
        planets = {
            "Sun (Surya)": swe.SUN, "Moon (Chandra)": swe.MOON, "Mars (Mangal)": swe.MARS,
            "Mercury (Buddh)": swe.MERCURY, "Jupiter (Guru)": swe.JUPITER, 
            "Venus (Shukra)": swe.VENUS, "Saturn (Shani)": swe.SATURN, "Rahu": swe.MEAN_NODE
        }
        
        zodiac_signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        
        results = []
        for name, p_id in planets.items():
            pos, _ = swe.calc_ut(jd, p_id, swe.FLG_SIDEREAL)
            lon_deg = pos[0]
            sign_idx = int(lon_deg / 30)
            degree_in_sign = round(lon_deg % 30, 2)
            results.append(f"- {name}: {zodiac_signs[sign_idx]} ({degree_in_sign}°)")
            
        rahu_lon = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SIDEREAL)[0][0]
        ketu_lon = (rahu_lon + 180) % 360
        ketu_sign = zodiac_signs[int(ketu_lon / 30)]
        results.append(f"- Ketu: {ketu_sign} ({round(ketu_lon % 30, 2)}°)")

        chart_data = f"**BIRTH DATA:** {day}-{month}-{year} at {hour:02d}:{minute:02d} in {city}\n\n"
        chart_data += "**EXACT PLANETARY POSITIONS (Sidereal):**\n" + "\n".join(results)
        return chart_data

    except Exception as e:
        return f"Math Engine Error: {str(e)}"

# ==========================================
# 5. GROQ LLM AGENT INTEGRATION
# ==========================================
def call_groq_agent(system_prompt, user_prompt, model, json_mode=False):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }
    
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=90)
        res.raise_for_status()
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Groq API Error: {e}")
        return '{"error": "API generation failed."}'

# ==========================================
# 6. THE CORE PDF GENERATION THREAD
# ==========================================
def process_background_task(chat_id, user_text):
    try:
        send_message(chat_id, "⚙️ Calculating exact planetary mathematics (Swisseph)...")
        calculated_math = calculate_chart_logic(user_text)
        
        # ----------------------------------------
        # MASTER SYNTHESIZER (ENGLISH JSON)
        # ----------------------------------------
        send_message(chat_id, "🧠 Synthesizing Threat-First Executive Dossier...")
        
        eng_sys_prompt = """You are an Elite Vedic Astrological Auditor. 
        You must output ONLY a valid JSON object. 
        
        THREAT-FIRST SEQUENCING MANDATE: 
        For every life pillar, you MUST output three bullet points in this exact order:
        1. The Warning: State the severe afflictions or combust planets.
        2. The Support (Karmic Asset): State the positive placements that act as a shield.
        3. The Synthesis: Explain how to combine the support to survive the warning.
        
        JSON SCHEMA REQUIRED:
        {
          "temporal_narrative": {
            "psychological_baseline": "...",
            "historical_trajectory": "...",
            "present_trigger": "...",
            "expected_survival": "..."
          },
          "structural_analysis": {
            "wealth_and_career": "...",
            "relationships_and_property": "...",
            "vitality_and_subconscious": "..."
          },
          "ayurvedic_audit": "...",
          "remediation_protocol": {
            "suppressing_afflictions": "Lal Kitab and Daan suppression tactics.",
            "amplifying_assets": "Gemstone and Mantra amplification tactics."
          }
        }"""
        
        eng_json_str = call_groq_agent(eng_sys_prompt, f"[CHART MATH]:\n{calculated_math}", MODEL_MASTER_AGENT, json_mode=True)
        eng_data = json.loads(eng_json_str)

        # ----------------------------------------
        # TRANSLATOR AGENT (HINDI JSON)
        # ----------------------------------------
        send_message(chat_id, "🌐 Generating Clinical Hindi Translation...")
        
        hin_sys_prompt = """You are an elite Clinical Translator. 
        CRITICAL MANDATE: You are translating a JSON object from English to Hindi.
        YOU MUST NOT TRANSLATE THE JSON KEYS. The keys must remain exactly in English. 
        Only translate the string values into formal, clinical Hindi (Devanagari script).
        Output ONLY a valid JSON object."""
        
        hin_json_str = call_groq_agent(hin_sys_prompt, eng_json_str, MODEL_TRANSLATOR, json_mode=True)
        hin_data = json.loads(hin_json_str)

        # ----------------------------------------
        # HTML/PDF COMPILATION
        # ----------------------------------------
        send_message(chat_id, "📄 Assembling Final PDF Dossier...")
        
        css = """
        @page { size: letter; margin: 2cm; }
        body { font-family: 'Helvetica', sans-serif; font-size: 11pt; line-height: 1.6; color: #222; }
        h1 { color: #1a237e; font-size: 16pt; border-bottom: 2px solid #1a237e; padding-bottom: 5px; margin-top: 20px; }
        h2 { color: #333; font-size: 13pt; margin-top: 15px; }
        h3 { color: #555; font-size: 11pt; font-style: italic; }
        .alert { background-color: #ffebee; padding: 10px; border-left: 4px solid #d32f2f; margin-bottom: 15px; }
        """

        html_body = f"""
        <html><head><style>{css}</style></head><body>
        <h1>FORENSIC ASTROLOGICAL AUDIT (ENGLISH)</h1>
        
        <h2>I. Temporal Narrative</h2>
        <h3>Psychological Baseline</h3> {md_to_html(safe_get(eng_data, ["temporal_narrative", "psychological_baseline"]))}
        <h3>Present Trigger</h3> {md_to_html(safe_get(eng_data, ["temporal_narrative", "present_trigger"]))}
        
        <h2>II. Structural Integrity Analysis</h2>
        <h3>Wealth & Career</h3> {md_to_html(safe_get(eng_data, ["structural_analysis", "wealth_and_career"]))}
        <h3>Relationships & Property</h3> {md_to_html(safe_get(eng_data, ["structural_analysis", "relationships_and_property"]))}
        
        <h2>III. Ayurvedic Audit</h2>
        {md_to_html(safe_get(eng_data, ["ayurvedic_audit"]))}
        
        <h2>IV. Consolidated Upayas (Remediation)</h2>
        <div class="alert"><strong>Suppressing Afflictions:</strong> {md_to_html(safe_get(eng_data, ["remediation_protocol", "suppressing_afflictions"]))}</div>
        <div><strong>Amplifying Assets:</strong> {md_to_html(safe_get(eng_data, ["remediation_protocol", "amplifying_assets"]))}</div>
        
        <div style="page-break-before: always;"></div>
        
        <h1>फोरेंसिक ज्योतिषीय ऑडिट (HINDI)</h1>
        <h2>I. काल-मानसिक कथा</h2>
        <h3>मानसिक आधार</h3> {md_to_html(safe_get(hin_data, ["temporal_narrative", "psychological_baseline"]))}
        <h3>वर्तमान ट्रिगर</h3> {md_to_html(safe_get(hin_data, ["temporal_narrative", "present_trigger"]))}
        
        <h2>II. संरचनात्मक अखंडता विश्लेषण</h2>
        <h3>धन और करियर</h3> {md_to_html(safe_get(hin_data, ["structural_analysis", "wealth_and_career"]))}
        
        <h2>IV. समेकित उपाय (Remediation)</h2>
        <div class="alert"><strong>दोषों का दमन:</strong> {md_to_html(safe_get(hin_data, ["remediation_protocol", "suppressing_afflictions"]))}</div>
        <div><strong>संपत्तियों का प्रवर्धन:</strong> {md_to_html(safe_get(hin_data, ["remediation_protocol", "amplifying_assets"]))}</div>
        </body></html>
        """
        
        pdf_path = f"/tmp/Astrological_Audit_{int(time.time())}.pdf"
        if generate_pdf_weasyprint(html_body, pdf_path):
            send_document(chat_id, pdf_path)
            send_message(chat_id, "✅ **Audit Complete. PDF attached above.**")
        else:
            send_message(chat_id, "⚠️ PDF rendering failed. Review server logs.")
            
        # Update session with calculated math so follow-up Q&A can access it
        session = get_session(chat_id)
        if session:
            session["logic_breakdown"] = calculated_math
            save_session(chat_id, session)

    except Exception as e:
        send_message(chat_id, f"⚠️ CRITICAL SYSTEM FAILURE: {str(e)}")
        print(f"Background Task Error: {str(e)}")

# ==========================================
# 7. TELEGRAM WEBHOOK ROUTE
# ==========================================
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if "message" not in update or "text" not in update["message"]:
            return jsonify(status="ignored"), 200

        chat_id = update["message"]["chat"]["id"]
        user_text = update["message"]["text"].strip()
        session = get_session(chat_id)

        # Regex to catch birth details: DD-MM-YYYY HH:MM City
        match = re.search(r'(\d{1,2})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{4})\s+(\d{1,2})[:.](\d{2})\s+([A-Za-z\s]+)', user_text)

        # ----------------------------------------
        # STATE 0: BRAND NEW USER (PRIMARY ENGINE)
        # ----------------------------------------
        if match:
            send_message(chat_id, "⏳ Initiating Forensic Astrological Audit...")
            
            session = {"state": "ready_to_generate", "logic_breakdown": "Calculating..."}
            save_session(chat_id, session)
            
            threading.Thread(target=process_background_task, args=(chat_id, user_text)).start()
            return jsonify(status="success"), 200

        # ----------------------------------------
        # STATE 2: FOLLOW-UP Q&A
        # ----------------------------------------
        elif session and session.get("state") == "ready_to_generate":
            send_message(chat_id, "🔍 Analyzing your query against your baseline...")
            
            q_system_msg = "You are an Elite Vedic Astrological Auditor. Answer the follow-up question directly based on the provided chart data. THREAT-FIRST: State the negative/vulnerability first, then the supporting asset. Cite exact dates."
            q_prompt = f"[CHART DATA]\n{session.get('logic_breakdown', 'Data unavailable')}\n\n[USER QUESTION]\n{user_text}"
            
            answer = call_groq_agent(q_system_msg, q_prompt, MODEL_QA, json_mode=False)
            
            for i in range(0, len(answer), 3900):
                send_message(chat_id, answer[i:i + 3900])
                time.sleep(0.5)
                
            return jsonify(status="success"), 200

        # ----------------------------------------
        # FALLBACK: UNRECOGNIZED INPUT
        # ----------------------------------------
        else:
            welcome_msg = (
                "⚠️ **SYSTEM READY**\n\n"
                "Please submit birth details to initiate the audit.\n"
                "**Format:** `DD-MM-YYYY HH:MM City`\n"
                "**Example:** `14-10-1990 14:40 Mumbai`"
            )
            send_message(chat_id, welcome_msg)
            return jsonify(status="success"), 200

    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        return jsonify(status="error"), 500

# ==========================================
# 8. SERVER BOOT SEQUENCE
# ==========================================
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
