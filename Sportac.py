import asyncio
import os
import re
import requests
from playwright.async_api import async_playwright

# --- НАСТРОЙКИ ---
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
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    max_len = 3500
    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for part in parts:
        try:
            requests.post(url, data={"chat_id": chat_id, "text": part}, timeout=15)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

def get_team_abbr(team_name_raw):
    if not team_name_raw: return ""
    name = str(team_name_raw).lower().strip()
    for team_key, abbr in TEAM_MAPPING.items():
        if team_key in name: return f"({abbr})"
    return f"({name[:3].upper()})"

def format_years(years_raw):
    try:
        years = int(years_raw)
    except: return "на срок"
    if years == 1: return "на 1 год"
    elif 2 <= years <= 4: return f"на {years} года"
    else: return f"на {years} лет"

def format_cap_hit(val_raw):
    try: return f"${int(val_raw):,}"
    except: return f"${val_raw}"

def translate_trade(text):
    if "forfeit" in text.lower(): return text
    pattern = r"The (.+?) acquire (.+?) from the (.+?) for (.+)"
    match = re.search(pattern, text)
    if match:
        team1, p1, team2, p2 = match.groups()
        p1 = p1.replace(".", "").replace(" and ", " и ")
        p2 = p2.replace(".", "").replace(" and ", " и ")
        return f"{team1} обменяли {p2} на {p1} из {team2}"
    return text

async def main():
    extracted_signings = []
    trades = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        async def on_response(response):
            if "api_signings" in response.url:
                try:
                    data = await response.json()
                    # Ищем данные везде, где они могут быть
                    if isinstance(data, dict):
                        # Твой список полей: p_fn, p_ln, sign_city, cap_hit, len, lvl
                        # Собираем все, что приходит
                        if "rows" in data:
                            extracted_signings.extend(data["rows"])
                        elif "data" in data and "p" in data["data"]:
                            extracted_signings.extend(data["data"]["p"])
                except: pass
        page.on("response", on_response)
        
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded")
        await asyncio.sleep(15)
        
        await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded")
        await asyncio.sleep(15)
        
        all_trades = await page.evaluate("""() => Array.from(document.querySelectorAll('[x-html="row.details_nolinks"]')).map(el => el.innerText.trim())""")
        trades = [translate_trade(t) for t in all_trades if "The ID of this channel" not in t and len(t) > 20]
        
        await browser.close()

    # --- ФОРМИРОВАНИЕ ---
    s_list = []
    for item in extracted_signings[:3]:
        # Пытаемся взять данные из разных возможных ключей (включая те, что ты подсказал)
        fn = item.get('p_fn') or item.get('first_name') or ''
        ln = item.get('p_ln') or item.get('last_name') or ''
        name = f"{fn} {ln}".strip()
        
        team = item.get('team_name') or item.get('sign_city') or ''
        cap = item.get('cval') or item.get('cap_hit') or '0'
        length = item.get('len') or '0'
        lvl = str(item.get('lvl', '')).upper()
        
        ctype = "подписал контракт новичка" if "ELC" in lvl else "подписал контракт"
        line = f"• {name} {ctype} {format_years(length)} с кэпхитом {format_cap_hit(cap)} {get_team_abbr(team)}"
        s_list.append(line)
        
    t_list = [f"• {t}" for t in trades[:3]]

    message = f"🔥 3 ПОСЛЕДНИХ ПОДПИСАНИЯ:\n{'Нет данных' if not s_list else chr(10).join(s_list)}\n\n🤝 3 ПОСЛЕДНИХ ТРЕЙДА:\n{'Нет данных' if not t_list else chr(10).join(t_list)}"
    
    send_to_telegram(message)

if __name__ == "__main__":
    asyncio.run(main())
