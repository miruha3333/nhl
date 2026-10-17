import os
import json
import requests
from bs4 import BeautifulSoup

CACHE_FILE = "last_data_cache.json"
INJURIES_SNAPSHOT_FILE = "injuries_snapshot.json"

SIGNINGS_API = "https://puckpedia.com/data/api_signings?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A100%2C%22api_url%22%3A%22%2Fdata%2Fapi_signings%22%2C%22url%22%3A%22signings%22%2C%22defaultSort%22%3A%22sign_date%22%2C%22sortBy%22%3A%22sign_date%22%2C%22sortDirection%22%3A%22DESC%22%2C%22sortBySecondary%22%3A%22%22%2C%22sortDirectionSecondary%22%3A%22%22%7D"
TRADES_API = "https://puckpedia.com/data/api_trades?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A40%2C%22api_url%22%3A%22%2Fdata%2Fapi_trades%22%2C%22url%22%3A%22trades%22%2C%22defaultSort%22%3A%22trade_date%22%2C%22sortBy%22%3A%22trade_date%22%2C%22sortDirection%22%3A%22DESC%22%2C%22sortBySecondary%22%3A%22%22%2C%22sortDirectionSecondary%22%3A%22%22%7D"

def set_github_output(name, value):
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")
    print(f"Output {name}={value}")

def extract_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        inner = data.get('data', data)
        if isinstance(inner, list):
            return inner
        if isinstance(inner, dict):
            for key in ('p', 'rows', 'results', 'items', 'data'):
                if key in inner and isinstance(inner[key], list):
                    return inner[key]
    return []

def main():
    changes_detected = False
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/json",
        "X-Requested-With": "XMLHttpRequest"
    }

    # Загружаем кэши
    cache = {"signings": {"last_date": "", "last_id": ""}, "trades": {"last_date": "", "last_id": ""}, "waivers": {"seen": []}}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            pass

    injuries_snapshot = {}
    if os.path.exists(INJURIES_SNAPSHOT_FILE):
        try:
            with open(INJURIES_SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                injuries_snapshot = json.load(f)
        except Exception:
            pass

    # 1. Проверка подписаний (API)
    try:
        resp = requests.get(SIGNINGS_API, headers=headers, timeout=10)
        if resp.status_code == 200:
            items = extract_list(resp.json())
            if items:
                first = items[0]
                item_date = str(first.get("sign_date", "") or "")
                item_id = str(first.get("cid", "") or first.get("id", "") or "")
                last_date = cache.get("signings", {}).get("last_date", "")
                last_id = cache.get("signings", {}).get("last_id", "")
                if item_date > last_date or (item_date == last_date and item_id and item_id != last_id):
                    print("🔄 Найдены новые подписания!")
                    changes_detected = True
    except Exception as e:
        print(f"Ошибка проверки подписаний: {e}")

    # 2. Проверка трейдов (API)
    if not changes_detected:
        try:
            resp = requests.get(TRADES_API, headers=headers, timeout=10)
            if resp.status_code == 200:
                items = extract_list(resp.json())
                if items:
                    first = items[0]
                    item_date = str(first.get("trade_date", "") or "")
                    item_id = str(first.get("trade_id", "") or "")
                    last_date = cache.get("trades", {}).get("last_date", "")
                    last_id = cache.get("trades", {}).get("last_id", "")
                    if item_date > last_date or (item_date == last_date and item_id and item_id != last_id):
                        print("🔄 Найдены новые трейды!")
                        changes_detected = True
        except Exception as e:
            print(f"Ошибка проверки трейдов: {e}")

    # 3. Проверка Уэйвера (HTML)
    if not changes_detected:
        try:
            resp = requests.get("https://puckpedia.com/waiver-wire", headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                first_row = soup.find('tr')
                if first_row:
                    cells = first_row.find_all('td')
                    if cells:
                        player_name = cells[0].text.strip()
                        seen_waivers = set(cache.get("waivers", {}).get("seen", []))
                        # Проверяем, есть ли имя верхнего игрока в увиденных
                        clean_name = player_name.replace(",", "").strip()
                        if clean_name and not any(clean_name in seen for seen in seen_waivers):
                            print(f"🔄 Найден новый игрок на уэйвере: {clean_name}")
                            changes_detected = True
        except Exception as e:
            print(f"Ошибка проверки уэйвера: {e}")

    # 4. Проверка Травм (HTML)
    if not changes_detected:
        try:
            resp = requests.get("https://puckpedia.com/injuries", headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                player_links = soup.select("a.pp_link[href*='/player/']")
                known_names = set(injuries_snapshot.keys())
                
                # Проверяем первых 5 игроков из таблицы
                for link in player_links[:5]:
                    raw_name = link.text.strip()
                    if "," in raw_name:
                        parts = raw_name.split(",")
                        formatted_name = f"{parts[1].strip()} {parts[0].strip()}"
                    else:
                        formatted_name = raw_name
                        
                    if formatted_name and formatted_name not in known_names:
                        print(f"🔄 Найдена новая травма: {formatted_name}")
                        changes_detected = True
                        break
        except Exception as e:
            print(f"Ошибка проверки травм: {e}")

    # Принудительный запуск, если файлов кэша нет совсем
    if not changes_detected and not os.path.exists(CACHE_FILE):
        print("📦 Кэш отсутствует, требуется первичный запуск.")
        changes_detected = True

    # Финальный вердикт
    if changes_detected:
        set_github_output("changes", "true")
    else:
        print("💤 Изменений ни в одном из 4 разделов нет. Пропуск запуска Sportac.py.")
        set_github_output("changes", "false")

if __name__ == "__main__":
    main()
