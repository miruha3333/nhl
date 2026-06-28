import os
import json
import subprocess
import logging
import asyncio
from fastapi import FastAPI, BackgroundTasks
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

CACHE_FILE = "last_data_cache.json"
TRANSACTIONS_CACHE_FILE = "transactions_cache.json"

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

async def async_check():
    logger.info("Начинаем проверку обновлений через имперсонатор TLS (curl_cffi)...")
    need_to_run_parser = False
    
    urls = {
        "signings": 'https://puckpedia.com/data/api_signings?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%7D',
        "trades": 'https://puckpedia.com/data/api_trades?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%7D',
        "transactions": 'https://puckpedia.com/data/api_transactions?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%2C%22transaction_type%22%3A%22roster%22%7D'
    }
    
    captured_data = {"signings": None, "trades": None, "transactions": None}
    
    # Открываем сессию с имитацией отпечатка браузера Chrome 120
    async with AsyncSession() as session:
        for key, url in urls.items():
            logger.info(f"Запрашиваем API напрямую для {key}...")
            try:
                response = await session.get(
                    url,
                    impersonate="chrome120",
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Referer": "https://puckpedia.com/",
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    timeout=20
                )
                if response.status_code == 200:
                    captured_data[key] = response.json()
                    logger.info(f"Успешно получили чистый JSON для {key}!")
                else:
                    logger.error(f"Cloudflare отклонил запрос {key}. Статус: {response.status_code}")
            except Exception as e:
                logger.error(f"Не удалось выполнить запрос для {key}: {e}")
            
            await asyncio.sleep(2)  # Безопасная пауза между запросами

    # --- АНАЛИЗ ДАННЫХ ---
    
    if captured_data["signings"]:
        items = extract_list(captured_data["signings"])
        if items:
            current_id = str(items[0].get("cid", "") or items[0].get("id", ""))
            logger.info(f"ID последнего подписания на сайте: {current_id}")
            cache = {}
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            if current_id != cache.get("signings", {}).get("last_id", ""):
                logger.info("Обнаружены новые подписания!")
                need_to_run_parser = True

    if captured_data["trades"]:
        items = extract_list(captured_data["trades"])
        if items:
            current_id = str(items[0].get("trade_id", "") or items[0].get("id", ""))
            logger.info(f"ID последнего трейда на сайте: {current_id}")
            cache = {}
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            if current_id != cache.get("trades", {}).get("last_id", ""):
                logger.info("Обнаружены новые трейды!")
                need_to_run_parser = True

    if captured_data["transactions"]:
        items = extract_list(captured_data["transactions"])
        if items:
            current_id = str(items[0].get("transaction_id", "") or items[0].get("id", ""))
            logger.info(f"ID последней транзакции на сайте: {current_id}")
            tx_cache = {}
            if os.path.exists(TRANSACTIONS_CACHE_FILE):
                with open(TRANSACTIONS_CACHE_FILE, "r", encoding="utf-8") as f:
                    tx_cache = json.load(f)
            if current_id != tx_cache.get("last_id", ""):
                logger.info("Обнаружены новые транзакции!")
                need_to_run_parser = True

    # --- ИТОГОВОЕ РЕШЕНИЕ ---
    if need_to_run_parser:
        logger.info("Активация основного парсера github.py...")
        subprocess.run(["python3", "github.py"])
    else:
        logger.info("Изменений не найдено. Засыпаем.")

def check_for_updates():
    asyncio.run(async_check())

@app.get("/check")
def trigger_check(background_tasks: BackgroundTasks):
    background_tasks.add_task(check_for_updates)
    return {"status": "Checking started"}
