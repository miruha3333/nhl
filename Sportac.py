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
        subprocess.run(["git", "config", "--global", "user.name", "bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "bot@bot.com"], check=True)
        subprocess.run(["git", "add", CACHE_FILE], check=True)
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
            subprocess.run(["git", "commit", "-m", "update cache [skip ci]"], check=True)
            subprocess.run(["git", "push"], check=True)

def get_team_abbr(team_name_raw):
    clean_name = re.sub(r'<[^>]+>', '', str(team_name_raw)).lower().strip()
    for team_key, abbr in TEAM_MAPPING.items():
        if team_key in clean_name: return f"({abbr})"
    return f"({clean_name[:3].upper()})"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Эмуляция обычного браузера
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        # --- СБОР ПОДПИСАНИЙ ---
        print("Загрузка подписаний...")
        await page.goto("https://puckpedia.com/signings", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(10)
        
        extracted_signings = await page.evaluate('''() => {
            // Ищем все строки таблицы, в которых есть знак доллара (признак контракта)
            const rows = Array.from(document.querySelectorAll('tr'));
            return rows.filter(tr => tr.innerText.includes('$')).slice(0, 5).map(tr => {
                const cells = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
                return {
                    name: tr.innerText.split('\n')[0].trim(),
                    team: cells[1] || 'N/A',
                    cval: cells[2] || '0',
                    len: cells[3] || '1'
                };
            });
        }''')

        # --- СБОР ТРЕЙДОВ ---
        print("Загрузка трейдов...")
        await page.goto("https://puckpedia.com/trades", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(10)
        
        trades = await page.evaluate('''() => {
            // Ищем блоки с текстом трейдов
            const elements = Array.from(document.querySelectorAll('div'));
            return elements.filter(el => el.getAttribute('x-html') === 'row.details_nolinks')
                           .map(el => el.innerText.trim());
        }''')
        
        await browser.close()

    if not extracted_signings and not trades:
        print("Данные не найдены. Скрипт завершен.")
        return

    # Формирование и отправка
    lines = [f"{s['name']} — {s['cval']} на {s['len']} года {get_team_abbr(s['team'])}" for s in extracted_signings]
    trade_lines = [t for t in trades if len(t) > 15][:3]
    msg = "🔥 ПОДПИСАНИЯ:\n" + "\n".join(lines) + "\n\n🤝 ТРЕЙДЫ:\n" + "\n".join(trade_lines)
    
    current_sig = "|".join([s['name'] for s in extracted_signings] + trade_lines)
    if current_sig != get_last_cached_signature():
        token, chat_id = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT_ID")
        if token and chat_id:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": msg})
        save_to_cache_and_commit(current_sig)

if __name__ == "__main__":
    asyncio.run(main())
