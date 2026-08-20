# ==========================================
# PART 3: llm_engine.py (COGNITIVE ENGINE)
# ==========================================
import os
import requests
import json
import time

def call_groq_agent(system_prompt, user_prompt, models_list):
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        return '{"error": "API Key Missing"}'
        
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    
    # Enforce strict JSON object return from the API
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
                    time.sleep(15) # Wait out rate limit
                    continue
                else: 
                    print(f"API Error {res.status_code}: {res.text}", flush=True)
                    break
            except Exception as e: 
                print(f"Request Exception: {e}", flush=True)
                break
    return '{"error": "All models failed or timed out"}'

def generate_dialectic_insights(session_data, chat_id, send_message_func):
    # Shifted to 8b first to guarantee lightning-fast execution and avoid timeouts
    MASTER_MODELS = ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"]
    
    base_cognitive_rules = """You are an Elite Executive Astrological Advisor.
    [DIALECTIC LAWS]
    1. OBJECTIVITY: Frame negative traits as 'Strategic Vulnerabilities' to be managed. Do not be overly fatalistic.
    2. THE PIVOT: Provide purely behavioral and psychological strategic advice in the 'executive_pivot'. DO NOT list physical rituals or remedies (like copper, silver, etc.).
    3. FORMATTING: You MUST output a valid, raw JSON object. The text values inside the JSON must use HTML bullet points (<ul><li>) and bold tags (<b>) for scannability."""

    base_user_msg = f"Ascendant: {session_data['asc_sign']}\nData: {session_data['logic_breakdown']}"

    swarm_chapters = {
        "psychology": base_cognitive_rules + "\nAnalyze the native's psychological operating system. Output JSON with EXACTLY these keys: \"asset\", \"vulnerability\", \"executive_pivot\".",
        "career_wealth": base_cognitive_rules + "\nAnalyze career apex and wealth potential. Output JSON with EXACTLY these keys: \"asset\", \"vulnerability\", \"executive_pivot\".",
        "relational_karma": base_cognitive_rules + "\nAnalyze relationship karma based on D-9 Navamsha. Output JSON with EXACTLY these keys: \"asset\", \"vulnerability\", \"executive_pivot\".",
        "ayurvedic_audit": base_cognitive_rules + "\nAnalyze the primary Ayurvedic Dosha. Output JSON with EXACTLY these keys: \"asset\", \"vulnerability\", \"executive_pivot\".",
        "forecast": base_cognitive_rules + "\nAnalyze transits for the next 24 months. Output JSON with EXACTLY these keys: \"strategic_windows\", \"structural_threats\", \"executive_summary\"."
    }

    eng_data = {}
    for chapter_key, system_prompt in swarm_chapters.items():
        send_message_func(chat_id, f"🧠 Synthesizing: {chapter_key.replace('_', ' ').title()}...")
        raw_res = call_groq_agent(system_prompt, base_user_msg, MASTER_MODELS).strip()
        
        try:
            parsed_json = json.loads(raw_res)
            
            # Failsafe: Check if API returned our custom error payload
            if "error" in parsed_json:
                raise ValueError(f"API Error caught: {parsed_json['error']}")
                
            # Failsafe: Verify the expected keys actually exist so the PDF isn't blank
            if chapter_key == "forecast":
                if "strategic_windows" not in parsed_json: 
                    raise ValueError("Forecast keys missing")
            else:
                if "asset" not in parsed_json: 
                    raise ValueError("Standard keys missing")
                    
            eng_data[chapter_key] = parsed_json
            
        except Exception as e:
            print(f"Data parsing exception for {chapter_key}: {e}", flush=True)
            # If API fails or keys are missing, inject this visible HTML so the PDF doesn't render blank boxes
            error_html = "<ul><li><b>Data unavailable. The cognitive engine experienced a timeout or API rate limit. Please try again in 60 seconds.</b></li></ul>"
            
            if chapter_key == "forecast":
                eng_data[chapter_key] = {
                    "strategic_windows": error_html, 
                    "structural_threats": error_html, 
                    "executive_summary": error_html
                }
            else:
                eng_data[chapter_key] = {
                    "asset": error_html, 
                    "vulnerability": error_html, 
                    "executive_pivot": error_html
                }
                
        time.sleep(2)
        
    return eng_data
