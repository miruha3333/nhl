import os
import requests
import json

# --- КОНФИГУРАЦИЯ ---
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://puckpedia.com/",
    "X-Requested-With": "XMLHttpRequest"
}

def send_to_telegram(text):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    
    if not token or not chat_id:
        print("DEBUG: Ошибка - токены не найдены в окружении!")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    
    response = requests.post(url, data=payload)
    print(f"DEBUG: Статус отправки в ТГ: {response.status_code}")
    print(f"DEBUG: Ответ от ТГ: {response.text}")

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

def get_data():
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get("https://puckpedia.com/")
    
    signings_url = "https://puckpedia.com/data/api_signings"
    trades_url = "https://puckpedia.com/data/api_trades"
    params = {"q": '{"curPage":1,"pageSize":5}'}
    
    s_resp = session.get(signings_url, params=params)
    t_resp = session.get(trades_url, params=params)
    
    print(f"DEBUG: Ответ API подписаний (первые 100 симв): {s_resp.text[:100]}")
    
    if s_resp.status_code != 200:
        print(f"DEBUG: Ошибка доступа к подписаниям: {s_resp.status_code}")
        return [], []
        
    signings = s_resp.json().get("rows", [])
    trades_raw = t_resp.json().get("rows", [])
    trades = [t.get("details_nolinks", "") for t in trades_raw]
    
    return signings, trades

def main():
    print("Получение данных...")
    signings, trades = get_data()
    
    print(f"DEBUG: Найдено подписаний: {len(signings)}")
    print(f"DEBUG: Найдено трейдов: {len(trades)}")
    
    if not signings and not trades:
        print("DEBUG: Данные не получены — список пуст!")
        return
        
    msg = "--- ПОСЛЕДНИЕ 5 ПОДПИСАНИЙ ---\n" + "\n".join([format_signing(i) for i in signings])
    msg += "\n\n--- ПОСЛЕДНИЕ 5 ТРЕЙДОВ ---\n" + "\n".join(trades)
    
    print(f"DEBUG: Итоговое сообщение для ТГ:\n{msg}")
    send_to_telegram(msg)
    print("Работа скрипта завершена.")

if __name__ == "__main__":
    main()
