import os
import json
import subprocess
import logging
import asyncio
from fastapi import FastAPI, BackgroundTasks

# Настраиваем вывод логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

CACHE_FILE = "last_data_cache.json"
TRANSACTIONS_CACHE_FILE = "transactions_cache.json"

API_URLS = {
    "signings": "https://puckpedia.com/data/api_signings?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%7D",
    "trades": "https://puckpedia.com/data/api_trades?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%7D",
    "transactions": "https://puckpedia.com/data/api_transactions?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A5%2C%22transaction_type%22%3A%22roster%22%7D",
}

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

async def fetch_api(page, url):
    try:
        # Делаем запрос из контекста реального браузера, чтобы обойти 403
        api_response = await page.evaluate('''async (fetchUrl) => {
            const resp = await fetch(fetchUrl, {
                headers: {
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                }
            });
            const text = await resp.text();
            return {status: resp.status, body: text};
        }''', url)
        
        if api_response['status'] == 200:
            return json.loads(api_response['body'])
        else:
            logger.error(f"Ошибка API по адресу {url}: Статус {api_response['status']}")
    except Exception as e:
        logger.error(f"Не удалось извлечь данные API: {e}")
    return None

async def async_check():
    logger.info("Начинаем проверку обновлений через Playwright браузер...")
    need_to_run_parser = False
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Заходим на сайт как обычный человек для прохождения защиты куками
            await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)  # Даем сайту «принять» нас
        except Exception as e:
            logger.error(f"Сайт полностью заблокировал доступ браузеру: {e}")
            await browser.close()
            return

        # 1. ПРОВЕРКА ПОДПИСАНИЙ
        sign_data = await fetch_api(page, API_URLS["signings"])
        if sign_data:
            items = extract_list(sign_data)
            if items:
                current_id = str(items[0].get("cid", "") or items[0].get("id", ""))
                cache = {}
                if os.path.exists(CACHE_FILE):
                    with open(CACHE_FILE, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                if current_id != cache.get("signings", {}).get("last_id", ""):
                    logger.info("Обнаружены новые подписания!")
                    need_to_run_parser = True

        # 2. ПРОВЕРКА ТРЕЙДОВ
        trade_data = await fetch_api(page, API_URLS["trades"])
        if trade_data:
            items = extract_list(trade_data)
            if items:
                current_id = str(items[0].get("trade_id", "") or items[0].get("id", ""))
                cache = {}
                if os.path.exists(CACHE_FILE):
                    with open(CACHE_FILE, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                if current_id != cache.get("trades", {}).get("last_id", ""):
                    logger.info("Обнаружены новые трейды!")
                    need_to_run_parser = True

        # 3. ПРОВЕРКА ТРАНЗАКЦИЙ
        tx_data = await fetch_api(page, API_URLS["transactions"])
        if tx_data:
            items = extract_list(tx_data)
            if items:
                current_id = str(items[0].get("transaction_id", "") or items[0].get("id", ""))
                tx_cache = {}
                if os.path.exists(TRANSACTIONS_CACHE_FILE):
                    with open(TRANSACTIONS_CACHE_FILE, "r", encoding="utf-8") as f:
                        tx_cache = json.load(f)
                if current_id != tx_cache.get("last_id", ""):
                    logger.info("Обнаружены новые транзакции!")
                    need_to_run_parser = True

        await browser.close()

    # Финал: запускаем основной парсер, если нашли хоть одно изменение
    if need_to_run_parser:
        logger.info("Активация основного парсера github.py...")
        subprocess.run(["python3", "github.py"])
    else:
        logger.info("Изменений на сайте не найдено. Засыпаем.")

def check_for_updates():
    # Запускаем асинхронный движок внутри синхронного фонового процесса
    asyncio.run(async_check())

@app.get("/check")
def trigger_check(background_tasks: BackgroundTasks):
    background_tasks.add_task(check_for_updates)
    return {"status": "Checking started"}
