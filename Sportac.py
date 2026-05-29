import asyncio
import os
import re
import json
import subprocess
from curl_cffi import requests

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

# Имитируем чистый AJAX/Fetch запрос от браузера
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://puckpedia.com",
    "Referer": "https://puckpedia.com/signings"
}

def get_last_cached_signature():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_to_cache_and_commit(new_signature):
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
                print("Кэш успешно сохранен в репозиторий GitHub.")
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
    
    import requests as tg_req
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    max_len = 3500
    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for part in parts:
        try:
            tg_req.post(url, data={"chat_id": chat_id, "text": part}, timeout=15)
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")

def get_team_abbr(team_name_raw):
    if not team_name_raw: return ""
    # Если внутри названия команды зашит HTML (например, логотип/картинка), очищаем его
    clean_name = re.sub(r'<[^>]+>', '', str(team_name_raw)).lower().strip()
    for team_key, abbr in TEAM_MAPPING.items():
        if team_key in clean_name: return f"({abbr})"
    return f"({clean_name[:3].upper()})"

def format_years(years_raw):
    try:
        years = int(re.sub(r'[^0-9]', '', str(years_raw)))
    except:
        return "на срок"
    if years == 1: return "на 1 год"
    elif 2 <= years <= 4: return f"на {years} года"
    else: return f"на {years} лет"

def format_cap_hit(val_raw):
    try:
        clean_val = int(re.sub(r'[^0-9]', '', str(val_raw)))
        return f"${clean_val:,}"
    except:
        return f"${val_raw}"

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

    # Строки параметров запросов, которые ты вытащил из вкладки Network
    signings_q = '{"curPage":1,"pageSize":100,"api_url":"/data/api_signings","url":"signings","defaultSort":"sign_date","sortBy":"sign_date","sortDirection":"DESC","sortBySecondary":"","sortDirectionSecondary":""}'
    trades_q = '{"curPage":1,"pageSize":40,"api_url":"/data/api_trades","url":"trades","defaultSort":"trade_date","sortBy":"trade_date","sortDirection":"DESC","sortBySecondary":"","sortDirectionSecondary":""}'

    # --- 1. СБОР ПОДПИСАНИЙ ИЗ ОФИЦИАЛЬНОГО JSON API ---
    try:
        url = f"https://puckpedia.com/data/api_signings?q={signings_q}"
        # curl_cffi идеально имитирует TLS-отпечаток Хрома, обходя Cloudflare на GitHub Actions
        res = requests.get(url, headers=HEADERS, impersonate="chrome", timeout=20)
        if res.status_code == 200:
            res_json = res.json()
            if isinstance(res_json, dict) and "rows" in res_json:
                extracted_signings = res_json["rows"]
        else:
            print(f"Ошибка API подписаний. Статус-код: {res.status_code}")
    except Exception as e:
        print(f"Исключение при выполнении запроса подписаний: {e}")

    # --- 2. СБОР ТРЕЙДОВ ИЗ ОФИЦИАЛЬНОГО JSON API ---
    try:
        url = f"https://puckpedia.com/data/api_trades?q={trades_q}"
        res = requests.get(url, headers=HEADERS, impersonate="chrome", timeout=20)
        if res.status_code == 200:
            res_json = res.json()
            if isinstance(res_json, dict) and "rows" in res_json:
                for row in res_json["rows"]:
                    html_text = row.get("details_nolinks", "")
                    # Избавляемся от HTML-ссылок в тексте трейда
                    clean_text = re.sub(r'<[^>]+>', '', html_text).strip()
                    if clean_text and "The ID of this channel" not in clean_text and len(clean_text) > 20:
                        trades.append(translate_trade(clean_text))
        else:
            print(f"Ошибка API трейдов. Статус-код: {res.status_code}")
    except Exception as e:
        print(f"Исключение при выполнении запроса трейдов: {e}")

    if not extracted_signings and not trades:
        print("Внимание: Никакие данные не собрались. Операция прервана.")
        return

    # --- СБОРКА И ПРОВЕРКА КЭША ---
    s_list = []
    current_signature_elements = []

    # Обрабатываем 3 последних подписания
    for item in extracted_signings[:3]:
        # Получаем чистые имя и фамилию
        first_name = re.sub(r'<[^>]+>', '', str(item.get('p_fn', ''))).strip()
        last_name = re.sub(r'<[^>]+>', '', str(item.get('p_ln', ''))).strip()
        name = f"{first_name} {last_name}".strip()
        if not name: continue
        
        current_signature_elements.append(name)
        
        lvl = str(item.get("lvl", "")).upper()
        
        # Получаем чистое числовое значение контракта
        raw_cval = str(item.get('cval', 0) or 0)
        try:
            total_val = float(re.sub(r'[^0-9.]', '', raw_cval) or 0)
        except:
            total_val = 0
            
        years = int(item.get('len') or 1)
        cap_val = total_val / years if "ELC" in lvl else total_val
        
        ctype = "подписал контракт новичка" if "ELC" in lvl else "подписал контракт"
        line = f"{name} {ctype} {format_years(years)} с кэпхитом {format_cap_hit(cap_val)} {get_team_abbr(item.get('team_name'))}"
        s_list.append(line)
        
    # Обрабатываем 3 последних трейда
    t_list = trades[:3]
    for t in t_list:
        current_signature_elements.append(t[:50])

    # Проверяем изменения по уникальному отпечатку (сигнатуре)
    current_signature = "|".join(current_signature_elements)
    last_cached_signature = get_last_cached_signature()

    if current_signature == last_cached_signature:
        print("Новых событий на сайте нет. Отмена отправки.")
        return
    
    # Формируем и отправляем итоговое сообщение
    message = f"🔥 3 ПОСЛЕДНИХ ПОДПИСАНИЯ:\n\n{chr(10).join([s + chr(10) for s in s_list])}\n🤝 3 ПОСЛЕДНИХ ТРЕЙДА:\n\n{chr(10).join([t + chr(10) for t in t_list])}"
    
    send_to_telegram(message)
    save_to_cache_and_commit(current_signature)

if __name__ == "__main__":
    asyncio.run(main())
