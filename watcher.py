import os
import json
import requests

CACHE_FILE = "last_data_cache.json"

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
    headers = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}

    cache = {"signings": {"last_date": "", "last_id": ""}, "trades": {"last_date": "", "last_id": ""}}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            pass

    # Проверка подписаний
    try:
        resp = requests.get(SIGNINGS_API, headers=headers, timeout=15)
        if resp.status_code == 200:
            items = extract_list(resp.json())
            if items:
                first = items[0]
                item_date = str(first.get("sign_date", "") or "")
                item_id = str(first.get("cid", "") or first.get("id", "") or "")
                last_date = cache.get("signings", {}).get("last_date", "")
                last_id = cache.get("signings", {}).get("last_id", "")
                print(f"API Signings: с сайта дата '{item_date}' (id: {item_id}), в кэше дата '{last_date}' (id: {last_id})")
                if item_date > last_date or (item_date == last_date and item_id and item_id != last_id):
                    print("🔄 Найдены новые подписания!")
                    changes_detected = True
    except Exception as e:
        print(f"Ошибка проверки подписаний: {e}")

    # Проверка трейдов
    if not changes_detected:
        try:
            resp = requests.get(TRADES_API, headers=headers, timeout=15)
            if resp.status_code == 200:
                items = extract_list(resp.json())
                if items:
                    first = items[0]
                    item_date = str(first.get("trade_date", "") or "")
                    item_id = str(first.get("trade_id", "") or "")
                    last_date = cache.get("trades", {}).get("last_date", "")
                    last_id = cache.get("trades", {}).get("last_id", "")
                    print(f"API Trades: с сайта дата '{item_date}' (id: {item_id}), в кэше дата '{last_date}' (id: {last_id})")
                    if item_date > last_date or (item_date == last_date and item_id and item_id != last_id):
                        print("🔄 Найдены новые трейды!")
                        changes_detected = True
    except Exception as e:
        print(f"Ошибка проверки трейдов: {e}")

    if not changes_detected and not os.path.exists(CACHE_FILE):
        print("📦 Кэш отсутствует, требуется запуск.")
        changes_detected = True

    if changes_detected:
        set_github_output("changes", "true")
    else:
        print("💤 Изменений нет.")
        set_github_output("changes", "false")

if __name__ == "__main__":
    main()
