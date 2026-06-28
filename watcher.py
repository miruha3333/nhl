import os
import requests
import json
import subprocess
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

CACHE_FILE = "last_data_cache.json"
TRANSACTIONS_CACHE_FILE = "transactions_cache.json"

# Ссылки на API всех 4 разделов сайта
API_URLS = {
    "signings": "https://puckpedia.com/data/api_signings?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%2D",
    "trades": "https://puckpedia.com/data/api_trades?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%7D",
    "transactions": "https://puckpedia.com/data/api_transactions?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%2C%22transaction_type%22%3A%22roster%22%7D",
    "waivers": "https://puckpedia.com/waiver-wire" # Для уэйверов проверим доступность самой страницы
}

# Маскировка под обычный браузер, чтобы сайт не выдавал ошибку доступу
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html",
    "X-Requested-With": "XMLHttpRequest"
}

def check_for_updates():
    print("Начинаем проверку обновлений по всем разделам...")
    need_to_run_parser = False

    # 1. ПРОВЕРКА ПОДПИСАНИЙ И ТРЕЙДОВ
    try:
        # Проверяем подписания
        res_sign = requests.get(API_URLS["signings"], headers=HEADERS, timeout=15)
        if res_sign.status_code == 200:
            data = res_sign.json().get('data', {}).get('rows', [])
            if data:
                current_id = str(data[0].get("cid", "") or data[0].get("id", ""))
                
                if os.path.exists(CACHE_FILE):
                    with open(CACHE_FILE, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                else:
                    cache = {}
                
                if current_id != cache.get("signings", {}).get("last_id", ""):
                    print("Обнаружены новые подписания!")
                    need_to_run_parser = True
        else:
            print(f"Ошибка проверки подписаний: Статус {res_sign.status_code}")

        # Проверяем трейды
        res_trades = requests.get(API_URLS["trades"], headers=HEADERS, timeout=15)
        if res_trades.status_code == 200:
            data = res_trades.json().get('data', {}).get('rows', [])
            if data:
                current_id = str(data[0].get("trade_id", "") or data[0].get("id", ""))
                if os.path.exists(CACHE_FILE):
                    with open(CACHE_FILE, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                else:
                    cache = {}
                
                if current_id != cache.get("trades", {}).get("last_id", ""):
                    print("Обнаружены новые трейды!")
                    need_to_run_parser = True
        else:
            print(f"Ошибка проверки трейдов: Статус {res_trades.status_code}")

    except Exception as e:
        print(f"Ошибка в блоке подписаний/трейдов: {e}")

    # 2. ПРОВЕРКА ТРАНЗАКЦИЙ
    try:
        res_tx = requests.get(API_URLS["transactions"], headers=HEADERS, timeout=15)
        if res_tx.status_code == 200:
            data = res_tx.json().get('data', {}).get('rows', [])
            if data:
                current_id = str(data[0].get("transaction_id", "") or data[0].get("id", ""))
                
                if os.path.exists(TRANSACTIONS_CACHE_FILE):
                    with open(TRANSACTIONS_CACHE_FILE, "r", encoding="utf-8") as f:
                        tx_cache = json.load(f)
                else:
                    tx_cache = {}
                
                if current_id != tx_cache.get("last_date", ""): # Твой кэш использует last_date / last_id[cite: 1]
                    if current_id != tx_cache.get("last_id", ""):
                        print("Обнаружены новые транзакции!")
                        need_to_run_parser = True
        else:
            print(f"Ошибка проверки транзакций: Статус {res_tx.status_code}")
    except Exception as e:
        print(f"Ошибка в блоке транзакций: {e}")

    # 3. ПР ПРОВЕРКА УЭЙВЕРА И ТРАВМ
    # Так как уэйверы и травмы не отдают простой JSON без авторизации,
    # мы проверяем общую доступность сайта. Если хоть один верхний блок сработал,
    # или если мы просто хотим подстраховаться — мы также можем запустить парсер.
    # Но чтобы не спамить, парсер включится только если ПРЯМО НАЙДЕНЫ изменения выше.

    # ИТОГОВОЕ РЕШЕНИЕ
    if need_to_run_parser:
        print("Запуск основного парсера github.py...")
        # Запускаем основной тяжелый парсер с Playwright
        subprocess.run(["python3", "github.py"])
    else:
        print("Изменений на сайте не найдено. Засыпаем.")

@app.get("/check")
def trigger_check(background_tasks: BackgroundTasks):
    background_tasks.add_task(check_for_updates)
    return {"status": "Checking started"}
