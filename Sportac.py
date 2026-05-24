import asyncio
import os
import re
import requests
from playwright.async_api import async_playwright

# --- НАСТРОЙКИ (СЛОВАРИ) ---
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

RUS_TEAM_MAPPING = {
    'Buffalo Sabres': 'Баффало (обменяли)', 'Carolina Hurricanes': 'Каролина (обменяла)',
    'Boston Bruins': 'Бостон (обменял)', 'Columbus Blue Jackets': 'Коламбус (обменял)',
    'Detroit Red Wings': 'Детройт (обменял)', 'New Jersey Devils': 'Нью-Джерси (обменяли)',
    'Montreal Canadiens': 'Монреаль (обменял)', 'New York Islanders': 'Айлендерс (обменял)',
    'Ottawa Senators': 'Оттава (обменяла)', 'New York Rangers': 'Рейнджерс (обменяли)',
    'Tampa Bay Lightning': 'Тампа (обменяла)', 'Philadelphia Flyers': 'Филадельфия (обменяла)',
    'Toronto Maple Leafs': 'Торонто (обменяло)', 'Pittsburgh Penguins': 'Питтсбург (обменял)',
    'Florida Panthers': 'Флорида (обменяла)', 'Washington Capitals': 'Вашингтон (обменял)',
    'Chicago Blackhawks': 'Чикаго (обменяло)', 'Anaheim Ducks': 'Анахайм (обменял)',
    'Colorado Avalanche': 'Колорадо (обменяло)', 'Calgary Flames': 'Калгари (обменяли)',
    'Dallas Stars': 'Даллас (обменял)', 'Edmonton Oilers': 'Эдмонтон (обменял)',
    'Minnesota Wild': 'Миннесота (обменяла)', 'Los Angeles Kings': 'Лос-Анджелес (обменял)',
    'Nashville Predators': 'Нэшвилл (обменял)', 'San Jose Sharks': 'Сан-Хосе (обменяло)',
    'St. Louis Blues': 'Сент-Луис (обменял)', 'Seattle Kraken': 'Сиэттл (обменял)',
    'Utah Mammoth': 'Юта (обменяла)', 'Vancouver Canucks': 'Ванкувер (обменял)',
    'Winnipeg Jets': 'Виннипег (обменял)'
}

# --- ФУНКЦИИ ---
def translate_rus_team(name):
    for eng, rus in RUS_TEAM_MAPPING.items():
        if eng.lower().split()[0] in name.lower(): return rus
    return name

def translate_trade(text):
    if "forfeit" in text.lower(): return text
    match = re.search(r"The (.+?) acquire (.+?) from the (.+?) for (.+)", text)
    if match:
        t1, p1, t2, p2 = match.groups()
        return f"{translate_rus_team(t1)} {p2.replace('and', 'и')} на {p1.replace('and', 'и')} из {translate_rus_team(t2).split('(')[0]}"
    return text

async def main():
    extracted_signings = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Подписания
        await page.goto("https://puckpedia.com/signings")
        await page.wait_for_selector("tr[key]", timeout=15000)
        extracted_signings = await page.evaluate('''() => Array.from(document.querySelectorAll('tr[key]')).slice(0, 3).map(tr => ({
            name: tr.querySelector('.pp_link span')?.innerText || '',
            team: tr.querySelector('td:has([class*="sign_city"])')?.innerText || '',
            cap: tr.querySelector('td:has([class*="cap_hit"])')?.innerText.replace(/[^0-9]/g, '') || '0',
            len: tr.querySelector('td:has([class*="len"])')?.innerText || '1',
            lvl: tr.querySelector('td:has([class*="lvl"])')?.innerText || ''
        }))''')
        
        # Трейды
        await page.goto("https://puckpedia.com/trades")
        await page.wait_for_selector('[x-html="row.details_nolinks"]', timeout=15000)
        trades = await page.evaluate("""() => Array.from(document.querySelectorAll('[x-html="row.details_nolinks"]')).map(el => el.innerText.trim())""")
        await browser.close()

    # --- ФОРМИРОВАНИЕ ТЕКСТА ---
    s_list = []
    for s in extracted_signings:
        total = int(s['cap'])
        years = int(s['len'])
        cap_val = f"${(total // years):,}" if "ELC" in s['lvl'].upper() else f"${total:,}"
        ctype = "подписал контракт новичка" if "ELC" in s['lvl'].upper() else "подписал контракт"
        s_list.append(f"{s['name']} {ctype} на {s['len']} лет с кэпхитом {cap_val} ({s['team'][:3].upper()})")
        
    t_list = [translate_trade(t) for t in trades if "The ID" not in t and len(t) > 20][:3]

    msg = f"🔥 3 ПОСЛЕДНИХ ПОДПИСАНИЯ:\n\n{chr(10).join([s + chr(10) for s in s_list])}\n🤝 3 ПОСЛЕДНИХ ТРЕЙДА:\n\n{chr(10).join([t + chr(10) for t in t_list])}"
    
    # Отправка
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if token and chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": msg})

if __name__ == "__main__":
    asyncio.run(main())
