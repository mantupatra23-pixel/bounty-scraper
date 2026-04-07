import requests
import xml.etree.ElementTree as ET
from fastapi import FastAPI
from groq import Groq
import json
import os
import time
from datetime import datetime, timedelta

app = FastAPI(title="Mantu AI Secure Wealth Agent")

# --- 1. CONFIGURATION (USING ENV VARS) ---
# Token code mein nahi, Render ke Dashboard par daalein
TELEGRAM_BOT_TOKEN = "8750648444:AAHMzTRVsztmyjTaftHUAL-vAkurSO5EXZw"
TELEGRAM_CHAT_ID = "8304416413"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") # Render Dashboard se aayega
GROQ_API_KEY = os.getenv("GROQ_API_KEY")   # Render Dashboard se aayega
DB_FILE = "ultimate_wealth_db.json"

# Experience Matrix
MY_STRENGTHS = {
    "AI": "Founder of VISORA AI (SaaS), Expert in Llama 3/Ollama automation.",
    "Web": "Next.js 15, FastAPI, Tailwind CSS, Full-stack Automation.",
    "Web3": "Solidity, Rust (Solana), Smart Contract Auditing."
}

# Initializing Client only if API Key exists
client = None
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)

# --- 2. DATABASE HANDLER ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {"seen": [], "applied": []}
    return {"seen": [], "applied": []}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

# --- 3. THE HAND: AUTO-COMMENT ---
def auto_comment_github(issue_url, solution_pitch):
    if not GITHUB_TOKEN: return False
    try:
        parts = issue_url.split('/')
        owner, repo, issue_num = parts[3], parts[4], parts[6]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}/comments"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        res = requests.post(api_url, headers=headers, json={"body": solution_pitch}, timeout=10)
        return res.status_code == 201
    except: return False

# --- 4. THE BRAIN: AI REASONING ---
def get_commander_pitch(title, desc, source):
    if not client: return 0, "Missing API Key", ""
    prompt = f"""
    You are Mantu Patra's AI Business Manager. 
    Analyze this {source} task: {title}
    Description: {desc[:800]}
    My Portfolio: {json.dumps(MY_STRENGTHS)}
    
    Format:
    MATCH_SCORE: (0-10)
    HINDI_SUMMARY: (1 line)
    TECH_PLAN: (3 steps)
    PITCH: (Winning proposal in English)
    """
    try:
        res = client.chat.completions.create(model="llama3-8b-8192", messages=[{"role": "user", "content": prompt}], temperature=0.1)
        content = res.choices[0].message.content
        score = int(''.join(filter(str.isdigit, content.split('MATCH_SCORE:')[1].split('\n')[0])))
        pitch = content.split('PITCH:')[1].strip() if "PITCH:" in content else ""
        return score, content, pitch
    except: return 0, "AI Analysis Failed", ""

# --- 5. THE HUNTER: GLOBAL SCRAPER ---
def fetch_global_opportunities():
    jobs = []
    cutoff = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # GitHub Scout
    queries = ["label:bounty+state:open", "label:help-wanted+AI"]
    for q in queries:
        try:
            url = f"https://api.github.com/search/issues?q={q}+created:>{cutoff}&sort=created"
            r = requests.get(url, timeout=10).json()
            for item in r.get('items', [])[:3]:
                jobs.append({"id": str(item['id']), "t": item['title'], "l": item['html_url'], "d": item.get('body','') or "", "s": "GitHub"})
        except: continue

    # Web3 Scout
    try:
        rss = requests.get("https://web3.career/remote-jobs.rss", timeout=10)
        root = ET.fromstring(rss.content)
        for item in root.findall("./channel/item")[:2]:
            link = item.find("link").text
            jobs.append({"id": link, "t": item.find("title").text, "l": link, "d": item.find("description").text or "", "s": "Web3-Global"})
    except: pass
    return jobs

# --- 6. MAIN CONTROLLER ---
@app.get("/scrape")
async def start_autonomous_hunt():
    db = load_db()
    jobs = fetch_global_opportunities()
    new_found = 0

    for job in jobs:
        if job['id'] not in db['seen']:
            db['seen'].append(job['id'])
            new_found += 1
            
            score, full_intel, pitch = get_commander_pitch(job['t'], job['d'], job['s'])
            
            status = "🛰️ SCOUT DETECTED"
            if score >= 9 and job['s'] == "GitHub":
                if auto_comment_github(job['l'], pitch):
                    status = "🎖️ COMMANDER AUTO-WON"
                    db['applied'].append(job['id'])

            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": f"🌟 <b>{status} ({score}/10)</b>\n📌 {job['t']}\n🔗 <a href='{job['l']}'>OPEN MISSION</a>", "parse_mode": "HTML"})
            
            save_db(db)
            time.sleep(5) 

    return {"status": "Complete", "new": new_found}

@app.get("/")
def home(): return {"status": "Mantu AI Online", "applied": len(load_db()['applied'])}
