import asyncio
import os
import re
import subprocess
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

RUS_TEAM_MAPPING = {
    'Buffalo Sabres': {'main': 'Баффало обменяли', 'from': 'из Баффало'},
    'Carolina Hurricanes': {'main': 'Каролина обменяла', 'from': 'из Каролины'},
    'Boston Bruins': {'main': 'Бостон обменял', 'from': 'из Бостона'},
    'Columbus Blue Jackets': {'main': 'Коламбус обменял', 'from': 'из Коламбуса'},
    'Detroit Red Wings': {'main': 'Детройт обменял', 'from': 'из Детройта'},
    'New Jersey Devils': {'main': 'Нью-Джерси обменяли', 'from': 'из Нью-Джерси'},
    'Montreal Canadiens': {'main': 'Монреаль обменял', 'from': 'из Монреаля'},
    'New York Islanders': {'main': 'Айлендерс обменял', 'from': 'из Айлендерс'},
    'Ottawa Senators': {'main': 'Оттава обменяла', 'from': 'из Оттавы'},
    'New York Rangers': {'main': 'Рейнджерс обменяли', 'from': 'из Рейнджерс'},
    'Tampa Bay Lightning': {'main': 'Тампа обменяла', 'from': 'из Тампы'},
    'Philadelphia Flyers': {'main': 'Филадельфия обменяла', 'from': 'из Филадельфии'},
    'Toronto Maple Leafs': {'main': 'Торонто обменяло', 'from': 'из Торонто'},
    'Pittsburgh Penguins': {'main': 'Питтсбург обменял', 'from': 'из Питтсбурга'},
    'Florida Panthers': {'main': 'Флорида обменяла', 'from': 'из Флориды'},
    'Washington Capitals': {'main': 'Вашингтон обменял', 'from': 'из Вашингтона'},
    'Chicago Blackhawks': {'main': 'Чикаго обменяло', 'from': 'из Чикаго'},
    'Anaheim Ducks': {'main': 'Анахайм обменял', 'from': 'из Анахайма'},
    'Colorado Avalanche': {'main': 'Колорадо обменяло', 'from': 'из Колорадо'},
    'Calgary Flames': {'main': 'Калгари обменяли', 'from': 'из Калгари'},
    'Dallas Stars': {'main': 'Даллас обменял', 'from': 'из Далласа'},
    'Edmonton Oilers': {'main': 'Эдмонтон обменял', 'from': 'из Эдмонтона'},
    'Minnesota Wild': {'main': 'Миннесота обменяла', 'from': 'из Миннесоты'},
    'Los Angeles Kings': {'main': 'Лос-Анджелес обменял', 'from': 'из Лос-Анджелеса'},
    'Nashville Predators': {'main': 'Нэшвилл обменял', 'from': 'из Нэшвилла'},
    'San Jose Sharks': {'main': 'Сан-Хосе обменяло', 'from': 'из Сан-Хосе'},
    'St. Louis Blues': {'main': 'Сент-Луис обменял', 'from': 'из Сент-Луиса'},
    'Seattle Kraken': {'main': 'Сиэттл обменял', 'from': 'из Сиэттла'},
    'Utah Mammoth': {'main': 'Юта обменяла', 'from': 'из Юты'},
    'Vancouver Canucks': {'main': 'Ванкувер обменял', 'from': 'из Ванкувера'},
    'Winnipeg Jets': {'main': 'Виннипег обменял', 'from': 'из Виннипега'}
}

CACHE_FILE = "last_data_cache.txt"

def get_last_cached_signature():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_to_cache_and_commit(new_signature):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(new_signature)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", CACHE_FILE], check=True)
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
            subprocess.run(["git", "commit", "-m", "update cache [skip ci]"], check=True)
            subprocess.run(["git", "push"], check=True)

def get_rus_team_data(eng_name):
    clean_name = eng_name.strip()
    for key, value in RUS_TEAM_MAPPING.items():
        if clean_name.lower() in key.lower(): return value
    return {'main': f"{clean_name} обменял", 'from': f"из {clean_name}"}

def send_to_telegram(text):
    token, chat_id = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT_ID")
    if token and chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": text})

def get_team_abbr(team_name_raw):
    clean_name = re.sub(r'<[^>]+>', '', str(team_name_raw)).lower().strip()
    for team_key, abbr in TEAM_MAPPING.items():
        if team_key in clean_name: return f"({abbr})"
    return f"({clean_name[:3].upper()})"

async def main():
    async with async_playwright() as p:
        # Запуск с имитацией обычного пользователя
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        
        print("Загрузка PuckPedia...")
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded")
        await asyncio.sleep(20) # Ждем пока JS отрендерит данные
        
        # Общий селектор, который точно есть на странице
        extracted_signings = await page.evaluate('''() => {
            const rows = Array.from(document.querySelectorAll('table tr'));
            return rows.filter(r => r.innerText.includes('$')).slice(0, 5).map(tr => {
                const tds = tr.querySelectorAll('td');
                return {
                    text: tr.innerText,
                    team: tds[1]?.innerText || '',
                    cval: tds[2]?.innerText || '',
                    len: tds[3]?.innerText || ''
                };
            });
        }''')

        await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded")
        await asyncio.sleep(20)
        trades = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.trade-details, div')).filter(d => d.innerText.length > 30).slice(0, 3).map(d => d.innerText.trim());
        }''')
        await browser.close()

    if not extracted_signings:
        print("Данные не найдены, возможно капча.")
        return

    msg = "🔥 ПОДПИСАНИЯ:\n" + "\n".join([f"{s['text'].split('$')[0]}... — {s['cval']}" for s in extracted_signings])
    msg += "\n\n🤝 ТРЕЙДЫ:\n" + "\n".join(trades[:3])
    
    sig = str(extracted_signings) + str(trades)
    if sig != get_last_cached_signature():
        send_to_telegram(msg)
        save_to_cache_and_commit(sig)

if __name__ == "__main__":
    asyncio.run(main())
