# ==========================================
# PART 3: llm_engine.py (COGNITIVE ENGINE)
# ==========================================
import os
import requests
import json
import time
import re

def call_groq_agent(system_prompt, user_prompt, models_list):
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        return json.dumps({"error": "GROQ_API_KEY environment variable is missing."})
        
    groq_url = "https://api.groq.com/openai/v1/chat/completions"
    
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
                    time.sleep(15) # Wait out the rate limit
                    continue
                else:
                    print(f"API Error {res.status_code} for {model_name}: {res.text}", flush=True)
                    break # Model failed, try the next one in the list
            except Exception as e: 
                print(f"Request Exception for {model_name}: {e}", flush=True)
                break
                
    return json.dumps({"error": "All AI models timed out or failed."})

def generate_dialectic_insights(session_data, chat_id, send_message_func):
    # UPDATED TO GROQ'S ACTIVE MODELS (Post-August 2026 Purge)
    MASTER_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.6-27b"]
    
    base_cognitive_rules = """You are an Elite Executive Astrological Advisor.
    [DIALECTIC LAWS]
    1. OBJECTIVITY: Frame negative traits as 'Strategic Vulnerabilities' to be managed. Do not be overly fatalistic.
    2. THE PIVOT: Provide purely behavioral and psychological strategic advice in the 'executive_pivot'. DO NOT list physical rituals or remedies.
    3. FORMATTING: You MUST output a valid, raw JSON object. The text values inside the JSON must use HTML bullet points (<ul><li>) and bold tags (<b>) for scannability."""

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
        
        # Aggressive JSON extraction
        match = re.search(r'\{.*\}', raw_res, re.DOTALL)
        clean_json = match.group(0) if match else raw_res
        
        try:
            parsed_data = json.loads(clean_json)
            
            # Check if the API caught an error
            if "error" in parsed_data:
                raise ValueError(parsed_data["error"])
                
            # Verify keys exist
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
                
        # Hard sleep to prevent triggering free-tier limits
        time.sleep(8)
        
    return eng_data
