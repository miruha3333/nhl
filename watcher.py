import os
import json
import requests

CACHE_FILE = "last_data_cache.json"
INJURIES_SNAPSHOT_FILE = "injuries_snapshot.json"

SIGNINGS_API = "https://puckpedia.com/data/api_signings?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A100%2C%22api_url%22%3A%22%2Fdata%2Fapi_signings%22%2C%22url%22%3A%22signings%22%2C%22defaultSort%22%3A%22sign_date%22%2C%22sortBy%22%3A%22sign_date%22%2C%22sortDirection%22%3A%22DESC%22%2C%22sortBySecondary%22%3A%22%22%2C%22sortDirectionSecondary%22%3A%22%22%7D"
TRADES_API = "https://puckpedia.com/data/api_trades?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A40%2C%22api_url%22%3A%22%2Fdata%2Fapi_trades%22%2C%22url%22%3A%22trades%22%2C%22defaultSort%22%3A%22trade_date%22%2C%22sortBy%22%3A%22trade_date%22%2C%22sortDirection%22%3A%22DESC%22%2C%22sortBySecondary%22%3A%22%22%2C%22sortDirectionSecondary%22%3A%22%22%7D"
WAIVERS_API = "https://puckpedia.com/data/api_waivers?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A20%2C%22api_url%22%3A%22%2Fdata%2Fapi_waivers%22%2C%22url%22%3A%22waiver-wire%22%7D"
INJURIES_API = "https://puckpedia.com/data/api_injuries?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A30%2C%22api_url%22%3A%22%2Fdata%2Fapi_injuries%22%2C%22url%22%3A%22injuries%22%7D"

def set_github_output(name, value):
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        try:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write(f"{name}={value}\n")
        except Exception:
            pass
    print(f"Output {name}={value}")

def extract_list(data):
    try:
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
    except Exception:
        pass
    return []

def format_name(n):
    n = str(n).replace('\n', ' ').strip()
    if "," in n:
        parts = n.split(",")
        return f"{parts[1].strip()} {parts[0].strip()}"
    return n

def main():
    changes_detected = False
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }

    cache = {"signings": {"last_date": "", "last_id": ""}, "trades": {"last_date": "", "last_id": ""}, "waivers": {"seen": []}}
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
    except Exception:
        pass

    injuries_snapshot = {}
    try:
        if os.path.exists(INJURIES_SNAPSHOT_FILE):
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
                print(f"API Signings: сайт '{item_date}' (id: {item_id}), кэш '{last_date}' (id: {last_id})")
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
                    print(f"API Trades: сайт '{item_date}' (id: {item_id}), кэш '{last_date}' (id: {last_id})")
                    if item_date > last_date or (item_date == last_date and item_id and item_id != last_id):
                        print("🔄 Найдены новые трейды!")
                        changes_detected = True
        except Exception as e:
            print(f"Ошибка проверки трейдов: {e}")

    # 3. Проверка Уэйвера (API)
    if not changes_detected:
        try:
            resp = requests.get(WAIVERS_API, headers=headers, timeout=10)
            if resp.status_code == 200:
                items = extract_list(resp.json())
                seen_waivers = set(cache.get("waivers", {}).get("seen", []))
                for item in items[:5]:
                    p_fn = str(item.get('p_fn', '') or item.get('player_first_name', '')).strip()
                    p_ln = str(item.get('p_ln', '') or item.get('player_last_name', '')).strip()
                    player_name = f"{p_fn} {p_ln}".strip() or format_name(item.get('player_name', ''))
                    if player_name and player_name not in seen_waivers:
                        print(f"API Waivers: найден новый игрок '{player_name}'")
                        changes_detected = True
                        break
                print(f"API Waivers: прочитано {len(items)} записей")
        except Exception as e:
            print(f"Ошибка проверки уэйвера: {e}")

    # 4. Проверка Травм (API)
    if not changes_detected:
        try:
            resp = requests.get(INJURIES_API, headers=headers, timeout=10)
            if resp.status_code == 200:
                items = extract_list(resp.json())
                known_names = set(injuries_snapshot.keys())
                for item in items[:10]:
                    p_fn = str(item.get('p_fn', '') or item.get('player_first_name', '')).strip()
                    p_ln = str(item.get('p_ln', '') or item.get('player_last_name', '')).strip()
                    player_name = f"{p_fn} {p_ln}".strip() or format_name(item.get('player_name', ''))
                    if player_name and player_name not in known_names:
                        print(f"API Injuries: найдена новая травма '{player_name}'")
                        changes_detected = True
                        break
                print(f"API Injuries: прочитано {len(items)} записей")
        except Exception as e:
            print(f"Ошибка проверки травм: {e}")

    if not changes_detected and not os.path.exists(CACHE_FILE):
        print("📦 Кэш отсутствует, требуется первичный запуск.")
        changes_detected = True

    if changes_detected:
        set_github_output("changes", "true")
    else:
        print("💤 Изменений ни в одном из 4 разделов нет.")
        set_github_output("changes", "false")

if __name__ == "__main__":
    main()
