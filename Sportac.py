import asyncio
import re
import os
import requests
from playwright.async_api import async_playwright

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

def send_to_telegram(text):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id: return

    # Разбиваем текст на части по 3500 символов (безопасный лимит)
    max_len = 3500
    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for part in parts:
        try:
            r = requests.post(url, data={"chat_id": chat_id, "text": part}, timeout=15)
            if r.status_code != 200:
                print(f"Ошибка API Telegram: {r.text}")
        except Exception as e:
            print(f"Ошибка отправки: {e}")

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
    term = f" на {years} лет" if years else ""
    cap_value = item.get('cap_hit') or item.get('aav') or item.get('cval', '0')
    return f"{name} {ctype}{term} с кэпхитом ${cap_value} {get_team_abbr(item.get('team_name'))}"

def translate_trade(text):
    pattern = r"The (.+?) acquire (.+?) from the (.+?) for (.+)"
    match = re.search(pattern, text)
    if match:
        team1, p1, team2, p2 = match.groups()
        return f"{team1} получили {p1} от {team2} в обмен на {p2}"
    return text

async def main():
    signings = []
    trades = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()

        async def on_response(response):
            if "api_signings" in response.url:
                try:
                    data = await response.json()
                    if isinstance(data, dict) and "rows" in data:
                        signings.extend(data["rows"])
                except: pass

        page.on("response", on_response)
        
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded")
        await asyncio.sleep(15) 
        await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded")
        await asyncio.sleep(15)
        trades = await page.evaluate("() => Array.from(document.querySelectorAll('[x-html=\"row.details_nolinks\"]')).map(el => el.innerText.trim())")
        await browser.close()

    # Формируем сообщение
    s_list = [format_signing(i) for i in signings]
    t_list = [translate_trade(t) for t in trades]
    
    if not s_list and not t_list:
        return

    message = "🔥 ПОСЛЕДНИЕ ПОДПИСАНИЯ:\n" + ("\n".join(s_list) if s_list else "Нет данных")
    message += "\n\n🤝 ПОСЛЕДНИЕ ТРЕЙДЫ:\n" + ("\n".join(t_list) if t_list else "Нет данных")
    
    send_to_telegram(message)

if __name__ == "__main__":
    asyncio.run(main())
