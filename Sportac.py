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

def get_team_abbr(name):
    name = str(name).lower().strip()
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

        # 1. Парсинг подписаний через структуру таблицы
        await page.goto("https://puckpedia.com/signings", wait_until="networkidle")
        await asyncio.sleep(5)
        
        # Находим строки таблицы (пропускаем заголовок)
        rows = await page.query_selector_all("table tbody tr")
        signings = []
        for row in rows[:3]:
            # Извлекаем данные по селекторам, которые ты дал
            name = await row.eval_on_selector("td:nth-child(1)", "el => el.innerText") # Имя
            team = await row.eval_on_selector("td:nth-child(3)", "el => el.innerText") # Команда
            cap = await row.eval_on_selector("td:nth-child(4)", "el => el.innerText")  # Cap Hit
            years = await row.eval_on_selector("td:nth-child(5)", "el => el.innerText") # Лет
            lvl = await row.eval_on_selector("td:nth-child(6)", "el => el.innerText")   # Тип
            
            ctype = "контракт новичка" if "ELC" in lvl else "контракт"
            signings.append(f"• {name.strip()} | {ctype} на {years.strip()} года | Кэпхит: {cap.strip()} {get_team_abbr(team)}")

        # 2. Парсинг трейдов
        await page.goto("https://puckpedia.com/trades", wait_until="networkidle")
        await asyncio.sleep(5)
        all_trades = await page.evaluate("""() => Array.from(document.querySelectorAll('[x-html="row.details_nolinks"]')).map(el => el.innerText.trim())""")
        trades = [translate_trade(t) for t in all_trades if "The ID of this channel" not in t][:3]
        
        await browser.close()

    # Формирование сообщения
    message = "🔥 3 ПОСЛЕДНИХ ПОДПИСАНИЯ:\n" + ("\n".join(signings) if signings else "Нет данных")
    message += "\n\n🤝 3 ПОСЛЕДНИХ ТРЕЙДА:\n" + ("\n".join([f"• {t}" for t in trades]) if trades else "Нет данных")
    
    send_to_telegram(message)

if __name__ == "__main__":
    asyncio.run(main())
