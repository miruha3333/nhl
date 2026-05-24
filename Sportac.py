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
    requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=15)

def get_team_abbr(team_name_raw):
    name = str(team_name_raw).lower().strip()
    for team_key, abbr in TEAM_MAPPING.items():
        if team_key in name: return f"({abbr})"
    return f"({name[:3].upper()})"

def translate_trade(text):
    if "forfeit" in text.lower(): return text
    pattern = r"The (.+?) acquire (.+?) from the (.+?) for (.+)"
    match = re.search(pattern, text)
    if match:
        team1, p1, team2, p2 = match.groups()
        return f"{team1} обменяли {p2.replace('and', 'и')} на {p1.replace('and', 'и')} из {team2}"
    return text

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. Сбор подписаний через твои селекторы
        await page.goto("https://puckpedia.com/signings", wait_until="networkidle")
        # Ждем, пока прогрузятся элементы с классом sortActive (твои селекторы)
        await page.wait_for_selector('tr', timeout=20000)
        await asyncio.sleep(5) 

        signings = await page.evaluate('''() => {
            const rows = Array.from(document.querySelectorAll('tr[key]')).slice(0, 3);
            return rows.map(tr => {
                const name = tr.querySelector('.pp_link span')?.innerText || 'Unknown';
                const team = tr.querySelector('td:has([class*="sign_city"])')?.innerText || '';
                const cap = tr.querySelector('td:has([class*="cap_hit"])')?.innerText || '0';
                const len = tr.querySelector('td:has([class*="len"])')?.innerText || '0';
                return { name, team, cap, len };
            });
        }''')

        # 2. Парсинг трейдов
        await page.goto("https://puckpedia.com/trades", wait_until="networkidle")
        await asyncio.sleep(5)
        all_trades = await page.evaluate("""() => Array.from(document.querySelectorAll('[x-html="row.details_nolinks"]')).map(el => el.innerText.trim())""")
        trades = [translate_trade(t) for t in all_trades if "The ID of this channel" not in t and len(t) > 20][:3]
        
        await browser.close()

    # --- ФОРМИРОВАНИЕ ---
    s_list = [f"• {s['name']} на {s['len']} лет с кэпхитом {s['cap']} {get_team_abbr(s['team'])}" for s in signings]
    t_list = [f"• {t}" for t in trades]

    message = f"🔥 3 ПОСЛЕДНИХ ПОДПИСАНИЯ:\n{'Нет данных' if not s_list else chr(10).join(s_list)}\n\n🤝 3 ПОСЛЕДНИХ ТРЕЙДА:\n{'Нет данных' if not t_list else chr(10).join(t_list)}"
    send_to_telegram(message)

if __name__ == "__main__":
    asyncio.run(main())
