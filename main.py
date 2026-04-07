import requests
import xml.etree.ElementTree as ET
from fastapi import FastAPI
from groq import Groq
import json
import os
import time
from datetime import datetime, timedelta

app = FastAPI(title="Mantu AI Elite Agency")

# --- 1. CONFIGURATION (USING ENV VARS FOR SECURITY) ---
# Inhe Render ke Dashboard par "Environment Variables" mein daalein
TELEGRAM_BOT_TOKEN = "8750648444:AAHMzTRVsztmyjTaftHUAL-vAkurSO5EXZw"
TELEGRAM_CHAT_ID = "8304416413"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DB_FILE = "ultimate_wealth_db.json"

# Portfolio Data jo AI use karega winning pitches likhne ke liye
MY_STRENGTHS = {
    "AI": "Founder of VISORA AI, Expert in Llama 3/Ollama automation.",
    "FullStack": "Next.js 15, FastAPI, Tailwind CSS, Python Automation.",
    "Web3": "Solidity, Rust (Solana), Smart Contract Auditing.",
    "Experience": "Developer of automated SaaS and programmatic SEO engines."
}

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

# --- 3. AUTO-COMMENT (THE HAND) ---
def auto_comment_github(issue_url, pitch):
    if not GITHUB_TOKEN: return False
    try:
        parts = issue_url.split('/')
        owner, repo, issue_num = parts[3], parts[4], parts[6]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_num}/comments"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        res = requests.post(api_url, headers=headers, json={"body": pitch}, timeout=10)
        return res.status_code == 201
    except: return False

# --- 4. AI AGENT REASONING (THE BRAIN) ---
def get_commander_pitch(title, desc, source):
    if not client: return 0, "Missing API Key", ""
    prompt = f"""
    You are Mantu Patra's AI Business Manager. 
    Analyze this {source} task: {title}
    Description: {desc[:800]}
    
    My Portfolio Matrix: {json.dumps(MY_STRENGTHS)}
    
    INSTRUCTIONS:
    1. Score the task (0-10) based on my skills.
    2. Provide a 'Proof of Concept' code logic (brief).
    3. Write a professional winning proposal in English.

    Format:
    MATCH_SCORE: (Number)
    HINDI_SUMMARY: (1 line logic)
    TECH_PLAN: (3-step fix)
    CODE_LOGIC: (Brief pseudo-code or snippet)
    PITCH: (Final Proposal)
    """
    try:
        res = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = res.choices[0].message.content
        score = 0
        if "MATCH_SCORE:" in content:
            score_parts = content.split("MATCH_SCORE:")[1].split("\n")[0].strip()
            score = int(''.join(filter(str.isdigit, score_parts)))
        
        pitch = content.split('PITCH:')[1].strip() if "PITCH:" in content else ""
        return score, content, pitch
    except: return 0, "AI Analysis Error", ""

# --- 5. THE HUNTER: GLOBAL SCRAPER (THE EYES) ---
def fetch_global_opportunities():
    jobs = []
    cutoff = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # GitHub Scout (Bounties)
    queries = ["label:bounty+state:open", "label:help-wanted+AI"]
    for q in queries:
        try:
            url = f"https://api.github.com/search/issues?q={q}+created:>{cutoff}&sort=created"
            r = requests.get(url, timeout=10).json()
            for item in r.get('items', [])[:3]:
                jobs.append({
                    "id": str(item['id']), "t": item['title'], 
                    "l": item['html_url'], "d": item.get('body','') or "", "s": "GitHub"
                })
        except: continue

    # Web3 & Remote RSS Scout
    rss_feeds = [
        "https://web3.career/remote-jobs.rss",
        "https://remoteok.com/remote-python-jobs.rss"
    ]
    for rss in rss_feeds:
        try:
            r = requests.get(rss, timeout=10)
            root = ET.fromstring(r.content)
            for item in root.findall("./channel/item")[:2]:
                link = item.find("link").text
                jobs.append({
                    "id": link, "t": item.find("title").text, 
                    "l": link, "d": item.find("description").text or "", "s": "Global-Remote"
                })
        except: continue
    return jobs

# --- 6. MAIN CONTROLLER (THE AUTOPILOT) ---
@app.get("/scrape")
async def start_autonomous_hunt():
    db = load_db()
    jobs = fetch_global_opportunities()
    new_found = 0

    for job in jobs:
        if job['id'] not in db['seen']:
            db['seen'].append(job['id'])
            new_found += 1
            
            # AI Analysis & Pitch
            score, full_intel, pitch = get_commander_pitch(job['t'], job['d'], job['s'])
            
            status_tag = "🛰️ SCOUT DETECTED"
            
            # --- AUTO-APPLY LOGIC (GitHub Only) ---
            if score >= 9 and job['s'] == "GitHub":
                if auto_comment_github(job['l'], pitch):
                    status_tag = "🎖️ COMMANDER AUTO-WON"
                    db['applied'].append(job['id'])

            # Telegram Notification
            msg = (
                f"🌟 <b>{status_tag} (Score: {score}/10)</b>\n"
                f"--------------------------\n"
                f"📌 <b>{job['t']}</b>\n\n"
                f"🤖 <b>AI LOGIC:</b>\n{full_intel[:600]}...\n"
                f"--------------------------\n"
                f"🔗 <a href='{job['l']}'>OPEN MISSION</a>"
            )
            
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})
            
            save_db(db)
            time.sleep(5) 

    return {"status": "Mission Complete", "new_leads": new_found}

@app.get("/")
def home():
    db = load_db()
    return {"status": "Mantu AI Commander Live", "leads": len(db['seen']), "applied": len(db['applied'])}
