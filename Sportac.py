import asyncio
import os
import re
import requests
import subprocess
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
    """Читает сохраненный отпечаток прошлого поста из файла."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_to_cache_and_commit(new_signature):
    """Сохраняет новый отпечаток в файл и пушит его в репозиторий GitHub."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(new_signature)
    
    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", CACHE_FILE], check=True)
            
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", "Обновление кэша последних событий [skip ci]"], check=True)
                subprocess.run(["git", "push"], check=True)
                print("Кэш успешно сохранен в репозиторий.")
        except Exception as e:
            print(f"Не удалось сохранить кэш в Git: {e}")

def get_rus_team_data(eng_name):
    clean_name = eng_name.strip()
    for key, value in RUS_TEAM_MAPPING.items():
        if clean_name.lower() in key.lower():
            return value
    return {'main': f"{clean_name} обменял", 'from': f"из {clean_name}"}

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
    try: years = int(years_raw)
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
        rus_team1_data = get_rus_team_data(team1)
        rus_team2_data = get_rus_team_data(team2)
        
        p1 = p1.replace(".", "").replace(" and ", " и ")
        p2 = p2.replace(".", "").replace(" and ", " и ")
        
        return f"{rus_team1_data['main']} {p2} на {p1} {rus_team2_data['from']}"
    return text

async def main():
    extracted_signings = []
    trades = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Маскировка контекста для снижения подозрений у Cloudflare
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York"
        )
        page = await context.new_page()
        
        async def on_response(response):
            if "api_signings" in response.url:
                try:
                    data = await response.json()
                    if isinstance(data, dict):
                        if "data" in data and "p" in data["data"]: extracted_signings.extend(data["data"]["p"])
                        elif "rows" in data: extracted_signings.extend(data["rows"])
                except: pass
        page.on("response", on_response)
        
        # --- СБОР ПОДПИСАНИЙ ---
        try:
            await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(8)
        except Exception as e:
            print(f"Предупреждение по подписаниям: {e}")

        # Безопасный селектор tr без использования двоеточий
        if not extracted_signings:
            extracted_signings = await page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('table.pp_table2.stickycol.sortDesc tbody tr'));
                return rows.slice(0, 3).map(tr => {
                    const linkSpan = tr.querySelector('.pp_link span')?.innerText || '';
                    const nameParts = linkSpan.trim().split(' ');
                    return {
                        p_fn: nameParts[0] || '',
                        p_ln: nameParts.slice(1).join(' ') || '',
                        team_name: tr.querySelector('td:has([class*="sign_city"])')?.innerText || '',
                        cval: tr.querySelector('td:has([class*="cap_hit"])')?.innerText.replace(/[^0-9]/g, '') || '0',
                        len: tr.querySelector('td:has([class*="len"])')?.innerText || '1',
                        lvl: tr.querySelector('td:has([class*="lvl"])')?.innerText || ''
                    };
                });
            }''')
        
        # --- СБОР ТРЕЙДОВ ---
        try:
            await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(8)
        except Exception as e:
            print(f"Предупреждение по трейдам: {e}")
        
        all_trades = await page.evaluate("""() => Array.from(document.querySelectorAll('[x-html="row.details_nolinks"]')).map(el => el.innerText.trim())""")
        trades = [translate_trade(t) for t in all_trades if "The ID of this channel" not in t and len(t) > 20]
        
        await browser.close()

    # --- ФОРМИРОВАНИЕ ---
    s_list = []
    current_signature_elements = []

    for item in extracted_signings[:3]:
        name = f"{item.get('p_fn', '')} {item.get('p_ln', '')}".strip()
        current_signature_elements.append(name)
        
        lvl = str(item.get("lvl", "")).upper()
        total_val = float(item.get('cval', 0) or 0)
        years = int(item.get('len') or 1)
        cap_val = total_val / years if "ELC" in lvl else total_val
        ctype = "подписал контракт новичка" if "ELC" in lvl else "подписал контракт"
        line = f"{name} {ctype} {format_years(years)} с кэпхитом {format_cap_hit(cap_val)} {get_team_abbr(item.get('team_name'))}"
        s_list.append(line)
        
    t_list = trades[:3]
    for t in t_list:
        current_signature_elements.append(t[:50])

    # Сравнение с кэшем
    current_signature = "|".join(current_signature_elements)
    last_cached_signature = get_last_cached_signature()

    if current_signature == last_cached_signature:
        print("Новых подписаний и трейдов нет. Отмена отправки.")
        return
    
    # Исправлена опечатка 'as' -> 'for' в f-строке
    message = f"🔥 3 ПОСЛЕДНИХ ПОДПИСАНИЯ:\n\n{chr(10).join([s + chr(10) for s in s_list])}\n🤝 3 ПОСЛЕДНИХ ТРЕЙДА:\n\n{chr(10).join([t + chr(10) for t in t_list])}"
    
    send_to_telegram(message)
    save_to_cache_and_commit(current_signature)

if __name__ == "__main__":
    asyncio.run(main())
