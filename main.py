# ==========================================
# PART 5: main.py (THE ORCHESTRATOR)
# ==========================================
import os, requests, re, time, sqlite3, threading, json
from flask import Flask, request, jsonify

# MODULAR IMPORTS
from astro_math import calculate_sidereal_chart, calculate_vimshottari_timeline, get_applicable_remedies
from llm_engine import generate_dialectic_insights
from pdf_renderer import build_and_render_pdf

app = Flask(__name__)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
DB_PATH = os.environ.get("DB_PATH", "/tmp/bot.db")

# ==========================================
# DATABASE MANAGER (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (chat_id INTEGER PRIMARY KEY, session_data TEXT)''')
    conn.commit()
    conn.close()

def save_session(chat_id, data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO sessions (chat_id, session_data) VALUES (?, ?)", (chat_id, json.dumps(data)))
    conn.commit()
    conn.close()

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
    conn.commit()
    conn.close()

# ==========================================
# TELEGRAM HELPERS
# ==========================================
def send_message(chat_id, text):
    try: 
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except: 
        pass

def send_document(chat_id, file_path):
    try:
        with open(file_path, 'rb') as f: 
            requests.post(f"{TELEGRAM_API_URL}/sendDocument", data={'chat_id': chat_id}, files={'document': f}, timeout=30)
    except: 
        pass

# ==========================================
# BACKGROUND WORKER (Pipeline Execution)
# ==========================================
def process_background_task(chat_id, session_data):
    send_message(chat_id, "⏳ Executing Dialectic Intelligence Framework...")
    
    # 1. Generate JSON Insights via LLM Engine
    eng_data = generate_dialectic_insights(session_data, chat_id, send_message)
    
    # 2. Calculate Dasha Timeline via Math Engine
    timeline_data = calculate_vimshottari_timeline(session_data['planet_data']['Moon / Chandra']['lon'], session_data['dt_ist_iso'])
    
    send_message(chat_id, "🎨 Rendering Vector Layouts and Formatting PDF...")
    pdf_path = f"/tmp/Celestial_Strategy_{int(time.time())}.pdf"
    
    # 3. Build & Render PDF via PDF Engine
    if build_and_render_pdf(session_data, eng_data, timeline_data, pdf_path):
        send_document(chat_id, pdf_path)
    else:
        send_message(chat_id, "❌ Critical Error during PDF compilation.")

# ==========================================
# FLASK WEBHOOK
# ==========================================
@app.route('/', methods=['POST', 'GET'])
@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET': 
        return "Active Premium Modular Server", 200
    try:
        update = request.get_json(silent=True)
        if not update or "message" not in update or "text" not in update["message"]: 
            return jsonify(status="ignored"), 200
            
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
                res = requests.get(f"https://nominatim.openstreetmap.org/search?q={city_input}&format=json&limit=1", headers={'User-Agent': 'Bot/1.0'}, timeout=5).json()
                lat, lon = float(res[0]['lat']), float(res[0]['lon'])
                city_clean = res[0].get('display_name', city_input).split(',')[0]
            except: 
                lat, lon = 30.7333, 76.7794
                city_clean = city_input
                    
            asc_sign, planets, houses, sav, logic_breakdown, dt_ist = calculate_sidereal_chart(day, month, year, hour, minute, lat, lon)
            remedies = get_applicable_remedies(houses, planets)
            
            session = {
                "state": "ready", "asc_sign": asc_sign, "planet_data": planets, "houses": houses, "sav": sav, "dt_ist_iso": dt_ist,
                "remedies": remedies, "logic_breakdown": logic_breakdown,
                "birth_str": f"{day:02d}-{month:02d}-{year} at {hour:02d}:{minute:02d} in {city_clean}"
            }
            save_session(chat_id, session)
            
            threading.Thread(target=process_background_task, args=(chat_id, session)).start()
            return jsonify(status="success"), 200
            
    except Exception as e:
        print(f"CRITICAL Webhook Error: {str(e)}", flush=True)
        
    return jsonify(status="success"), 200

# ==========================================
# SERVER INITIALIZATION (Gunicorn Compatible)
# ==========================================
init_db()

if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
