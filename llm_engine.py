# ==========================================
# PART 3: llm_engine.py (COGNITIVE ENGINE)
# ==========================================
import os
import requests
import json
import time

def call_groq_agent(system_prompt, user_prompt, models_list):
    groq_key = os.environ.get("GROQ_API_KEY")
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
        payload = payload_base.copy(); payload["model"] = model_name
        for attempt in range(2):
            try:
                res = requests.post(groq_url, headers=headers, json=payload, timeout=180)
                if res.status_code == 200: 
                    return res.json()['choices'][0]['message']['content']
                elif res.status_code == 429: 
                    time.sleep(20)
                    continue
                else: 
                    break
            except: 
                break
    return '{"error": "Failed"}'

def generate_dialectic_insights(session_data, chat_id, send_message_func):
    MASTER_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "groq/compound", "llama3-70b-8192"]
    
    base_cognitive_rules = """You are an Elite Executive Astrological Advisor.
    [DIALECTIC LAWS]
    1. OBJECTIVITY: Do not sugarcoat, but do not be fatalistic. Frame negative traits as 'Strategic Vulnerabilities' to be managed.
    2. THE BRIDGE: You MUST weave the psychological rationale for the provided physical remedies into your 'executive_pivot' advice.
    3. FORMATTING: You must output a valid JSON object. The values must use HTML bullet points (<ul><li>) and bold tags (<b>) for scannability. NO long paragraphs. NO markdown."""

    remedies_text = " | ".join(session_data['remedies'])
    base_user_msg = f"Ascendant: {session_data['asc_sign']}\nData: {session_data['logic_breakdown']}\nPRESCRIBED REMEDIES TO EXPLAIN: {remedies_text}"

    swarm_chapters = {
        "psychology": base_cognitive_rules + "\nAnalyze the native's psychological operating system. Output JSON with exactly keys: 'asset', 'vulnerability', 'executive_pivot'.",
        "career_wealth": base_cognitive_rules + "\nAnalyze career apex and wealth potential. Output JSON with exactly keys: 'asset', 'vulnerability', 'executive_pivot'.",
        "relational_karma": base_cognitive_rules + "\nAnalyze relationship karma based on D-9 Navamsha. Output JSON with exactly keys: 'asset', 'vulnerability', 'executive_pivot'.",
        "ayurvedic_audit": base_cognitive_rules + "\nAnalyze the primary Ayurvedic Dosha. Output JSON with exactly keys: 'asset' (vitality strengths), 'vulnerability' (energy drains, no medical claims), 'executive_pivot'.",
        "forecast": base_cognitive_rules + "\nOutput JSON with exactly keys: 'strategic_windows', 'structural_threats', 'executive_summary'. Break down the upcoming 24-month timeline transits."
    }

    eng_data = {}
    for chapter_key, system_prompt in swarm_chapters.items():
        send_message_func(chat_id, f"🧠 Synthesizing: {chapter_key.replace('_', ' ').title()}...")
        raw_res = call_groq_agent(system_prompt, base_user_msg, MASTER_MODELS).strip()
        
        # Safe Markdown Clean-up
        if raw_res.startswith("```json"): raw_res = raw_res[7:]
        if raw_res.startswith("```"): raw_res = raw_res[3:]
        if raw_res.endswith("```"): raw_res = raw_res[:-3]
        
        try:
            eng_data[chapter_key] = json.loads(raw_res.strip())
        except:
            eng_data[chapter_key] = {"asset": "<b>Data parsing adjustment active.</b>", "vulnerability": "<b>Data parsing adjustment active.</b>", "executive_pivot": "<b>Data parsing adjustment active.</b>"}
            if chapter_key == "forecast":
                eng_data[chapter_key] = {"strategic_windows": "<b>Data parsing adjustment active.</b>", "structural_threats": "<b>Data parsing adjustment active.</b>", "executive_summary": "<b>Data parsing adjustment active.</b>"}
        time.sleep(3)
        
    return eng_data
