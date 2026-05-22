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
    if not token or not chat_id:
        print("Ошибка: Токены не найдены!")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        print("Данные отправлены в Telegram!")
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
    term = f"на {years} лет" if years else ""
    cap_value = item.get('cap_hit') or item.get('aav') or item.get('cval', '0')
    return f"{name} {ctype} {term} с кэпхитом ${cap_value} {get_team_abbr(item.get('team_name'))}"

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
        # Важно: добавляем User-Agent, чтобы не выглядеть как робот
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()

        # Слушаем ответы API
        async def on_response(response):
            if "api_signings" in response.url:
                try:
                    data = await response.json()
                    if isinstance(data, dict) and "rows" in data:
                        signings.extend(data["rows"])
                except: pass

        page.on("response", on_response)
        
        print("Загрузка страницы подписаний...")
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded")
        await asyncio.sleep(15) 

        print("Загрузка страницы трейдов...")
        await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded")
        await asyncio.sleep(15)
        trades = await page.evaluate("() => Array.from(document.querySelectorAll('[x-html=\"row.details_nolinks\"]')).map(el => el.innerText.trim())")
        await browser.close()

    # --- ОТПРАВКА ---
    s_text = "\n".join([format_signing(i) for i in signings[:5]])
    t_text = "\n".join([translate_trade(t) for t in trades[:5]])
    
    message = f"🔥 ПОСЛЕДНИЕ ПОДПИСАНИЯ:\n{s_text}\n\n🤝 ПОСЛЕДНИЕ ТРЕЙДЫ:\n{t_text}"
    send_to_telegram(message)

if __name__ == "__main__":
    asyncio.run(main())
