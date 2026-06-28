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
SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

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
    logger.info("Начинаем стабильную проверку обновлений через ScraperAPI...")
    
    if not SCRAPERAPI_KEY:
        logger.error("КРИТИЧЕСКАЯ ОШИБКА: Переменная SCRAPERAPI_KEY не найдена в Render!")
        return

    need_to_run_parser = False
    
    # Оригинальные эндпоинты PuckPedia
    target_urls = {
        "signings": 'https://puckpedia.com/data/api_signings?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%7D',
        "trades": 'https://puckpedia.com/data/api_trades?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%7D',
        "transactions": 'https://puckpedia.com/data/api_transactions?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%2C%22transaction_type%22%3A%22roster%22%7D'
    }
    
    captured_data = {"signings": None, "trades": None, "transactions": None}
    
    async with AsyncSession() as session:
        for key, target_url in target_urls.items():
            logger.info(f"Запрашиваем {key} через чистый прокси-канал...")
            
            # Формируем запрос через ScraperAPI, который сам обходит Cloudflare
            proxy_url = "http://api.scraperapi.com"
            payload = {
                "api_key": SCRAPERAPI_KEY,
                "url": target_url
            }
            
            try:
                response = await session.get(proxy_url, params=payload, timeout=30)
                
                if response.status_code == 200:
                    captured_data[key] = response.json()
                    logger.info(f"Успешно получили чистый JSON для {key}!")
                else:
                    logger.error(f"Ошибка прокси при запросе {key}. Статус: {response.status_code}. Ответ: {response.text[:100]}")
            except Exception as e:
                logger.error(f"Не удалось выполнить запрос для {key} через прокси: {e}")
            
            await asyncio.sleep(1)

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
        logger.info("Активация основного парсера parser.py...")
        subprocess.run(["python3", "parser.py"])
    else:
        logger.info("Изменений не найдено. Засыпаем.")

def check_for_updates():
    asyncio.run(async_check())

@app.get("/check")
def trigger_check(background_tasks: BackgroundTasks):
    background_tasks.add_task(check_for_updates)
    return {"status": "Checking started"}
