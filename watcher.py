import os
import json
import subprocess
import logging
import asyncio
from fastapi import FastAPI, BackgroundTasks

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
    logger.info("Начинаем облегченную проверку обновлений...")
    need_to_run_parser = False
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Блокируем мусор, чтобы экономить память
        async def block_heavy_resources(route):
            if route.request.resource_type in ["image", "font", "media", "stylesheet"]:
                await route.abort()
            else:
                await route.continue_()
        
        await page.route("**/*", block_heavy_resources)
        
        captured_data = {"signings": None, "trades": None, "transactions": None}
        
        # Улучшенный слушатель сети: теперь он покажет в логах, если поймал нужный URL
        async def handle_response(response):
            url = response.url
            if "api_signings" in url or "api_trades" in url or "api_transactions" in url:
                logger.info(f"Обнаружен сетевой запрос сайта: {url[:60]}... [Статус: {response.status}]")
                if response.status == 200:
                    try:
                        data = await response.json()
                        if "api_signings" in url:
                            captured_data["signings"] = data
                            logger.info("JSON подписаний успешно сохранен в память.")
                        elif "api_trades" in url:
                            captured_data["trades"] = data
                            logger.info("JSON трейдов успешно сохранен в память.")
                        elif "api_transactions" in url:
                            captured_data["transactions"] = data
                            logger.info("JSON транзакций успешно сохранен в память.")
                    except Exception as e:
                        logger.error(f"Ошибка разбора JSON: {e}")

        page.on("response", handle_response)

        # Перебираем страницы, увеличив паузу до 6 секунд для стабильности на Render
        for page_type, url in [
            ("signings", "https://puckpedia.com/signings"),
            ("trades", "https://puckpedia.com/trades"),
            ("transactions", "https://puckpedia.com/transactions")
        ]:
            try:
                logger.info(f"Открываем страницу {page_type}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(6)  # Даем 6 секунд, чтобы JS сайта успел запросить данные
            except Exception as e:
                logger.error(f"Ошибка при загрузке {page_type}: {e}")

        await browser.close()

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

    # --- ИТОГ ---
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
