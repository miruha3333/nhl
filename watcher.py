import os
import requests
import json
import subprocess
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

CACHE_FILE = "last_data_cache.json"
# Быстрый API PuckPedia, где видны самые свежие подписания
SIGNINGS_API = "https://puckpedia.com/data/api_signings?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%7D"

def check_for_updates():
    try:
        # 1. Делаем быстрый запрос без Playwright
        response = requests.get(SIGNINGS_API, headers={"Accept": "application/json"}, timeout=10)
        if response.status_code != 200:
            print("Сайт недоступен, засыпаем.")
            return

        data = response.json()
        # Извлекаем список записей
        rows = data.get('data', {}).get('rows', [])
        if not rows:
            return

        # Берем ID самого последнего подписания на сайте
        latest_site_id = str(rows[0].get("cid", "") or rows[0].get("id", ""))

        # 2. Читаем твой текущий кэш, чтобы узнать, что было обработано прошлый раз
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        else:
            cache = {}

        last_saved_id = cache.get("signings", {}).get("last_id", "")

        # 3. Сравниваем. Если ID совпадает — новинок нет
        if latest_site_id == last_saved_id:
            print("Новой информации нет. Засыпаем.")
            return
        
        # 4. Если ID другой — пошла новая инфа! Активируем твой основной парсер
        print("Обнаружена новая информация! Активируем парсер...")
        subprocess.run(["python3", "github.com"]) # Запуск твоего файла

    except Exception as e:
        print(f"Ошибка при проверке: {e}")

@app.get("/check")
def trigger_check(background_tasks: BackgroundTasks):
    # cron-job.org дернет этот URL, мы мгновенно ответим ему "ОК",
    # а проверку запустим в фоне, чтобы сайт не ругался на долгий ответ.
    background_tasks.add_task(check_for_updates)
    return {"status": "Checking started"}
