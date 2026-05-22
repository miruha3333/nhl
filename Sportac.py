import asyncio
import re
import os
import requests
from playwright.async_api import async_playwright

# --- КОНФИГУРАЦИЯ ---
TEAM_MAPPING = {
    'utah': 'UTAH', 'mammoth': 'UTAH', 'blue jackets': 'CBJ', 'bluejackets': 'CBJ',
    'predators': 'NAS', 'ducks': 'ANA', 'jets': 'WPG', 'wild': 'MIN', 'islanders': 'NYI',
    'rangers': 'NYR', 'kings': 'LAK', 'sabres': 'BUF', 'blackhawks': 'CHI', 'golden knights': 'VGK',
    'canucks': 'VAN', 'flyers': 'PHI', 'bruins': 'BOS', 'sharks': 'SJS', 'hurricanes': 'CAR',
    'penguins': 'PIT', 'capitals': 'WSH', 'canadiens': 'MTL', 'senators': 'OTT', 'red wings': 'DET',
    'redwings': 'DET', 'maple leafs': 'TOR', 'mapleleafs': 'TOR', 'oilers': 'EDM', 'panthers': 'FLA',
    'lightning': 'TBL', 'stars': 'DAL', 'avalanche': 'COL', 'devils': 'NJD', 'kraken': 'SEA',
    'flames': 'CGY', 'blues': 'STL'
}

# --- ФУНКЦИЯ ОТПРАВКИ ---
def send_to_telegram(text):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text})

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_team_abbr(team_name_raw):
    if not team_name_raw: return ""
    name = str(team_name_raw).lower().strip()
    for team_key, abbr in TEAM_MAPPING.items():
        if team_key in name: return f"({abbr})"
    return f"({name[:3].upper()})"

def format_signing(item):
    name = f"{item.get('p_fn', '')} {item.get('p_ln', '')}".strip()
    lvl = item.get("lvl", "").upper()
    ctype = "подписал контракт новичка" if "ELC" in lvl else "подписал контракт"
    years = str(item.get('len', ''))
    if years == '1': term = "на 1 год"
    elif years in ['2', '3', '4']: term = f"на {years} года"
    elif years: term = f"на {years} лет"
    else: term = ""
    cap_value = item.get('cap_hit') or item.get('aav') or item.get('cval', '0')
    return f"{name} {ctype} {term} с кэпхитом ${cap_value} {get_team_abbr(item.get('team_name'))}"

def translate_trade(text):
    if "forfeit" in text.lower(): return text
    pattern = r"The (.+?) acquire (.+?) from the (.+?) for (.+)"
    match = re.search(pattern, text)
    if match:
        team1, p1, team2, p2 = match.groups()
        p1 = p1.replace(".", "").replace(" and ", " и ")
        p2 = p2.replace(".", "").replace(" and ", " и ")
        return f"The {team1} обменяли {p2} на {p1} из the {team2}".rstrip('.')
    return text

# --- ОСНОВНАЯ ЛОГИКА ---
async def main():
    signings, trades = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("response", lambda r: signings.extend(r.json()["data"]["p"]) if "api_signings" in r.url and "data" in r.json() else None)
        await page.goto("https://puckpedia.com/signings")
        await asyncio.sleep(10)
        await page.goto("https://puckpedia.com/trades")
        await asyncio.sleep(10)
        trades = await page.evaluate("""() => Array.from(document.querySelectorAll('[x-html="row.details_nolinks"]')).map(el => el.innerText.trim())""")
        await browser.close()
    
    msg = "--- ПОСЛЕДНИЕ 5 ПОДПИСАНИЙ ---\n" + "\n".join([format_signing(i) for i in signings[:5]])
    msg += "\n\n--- ПОСЛЕДНИЕ 5 ТРЕЙДОВ ---\n" + "\n".join([translate_trade(" ".join(t.split())) for t in trades[:5]])
    def send_to_telegram(text):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    
    print(f"DEBUG: Token starts with: {token[:5] if token else 'None'}...") # Выведет начало токена
    print(f"DEBUG: Chat ID: {chat_id}")
    
    if not token or not chat_id:
        print("Ошибка: Токены отсутствуют!")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(url, data={"chat_id": chat_id, "text": text})
    
    print(f"DEBUG: Telegram Response Status: {response.status_code}")
    print(f"DEBUG: Telegram Response Body: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
