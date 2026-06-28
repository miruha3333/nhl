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
        # Ограничиваем аппетиты Chromium, чтобы уместиться в 512МБ лимит Render
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-dev-shm-usage", 
                "--disable-gpu"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # ЭКОНОМИЯ ПАМЯТИ: Блокируем загрузку картинок, шрифтов, видео и стилей.
        # Нам нужен только текст и запросы к API, остальное — мусор.
        async def block_heavy_resources(route):
            if route.request.resource_type in ["image", "font", "media", "stylesheet"]:
                await route.abort()
            else:
                await route.continue_()
        
        await page.route("**/*", block_heavy_resources)
        
        captured_data = {"signings": None, "trades": None, "transactions": None}
        
        async def handle_response(response):
            url = response.url
            if response.status == 200:
                try:
                    if "api_signings" in url:
                        captured_data["signings"] = await response.json()
                        logger.info("Перехвачен API-ответ подписаний.")
                    elif "api_trades" in url:
                        captured_data["trades"] = await response.json()
                        logger.info("Перехвачен API-ответ трейдов.")
                    elif "api_transactions" in url:
                        captured_data["transactions"] = await response.json()
                        logger.info("Перехвачен API-ответ транзакций.")
                except Exception:
                    pass

        page.on("response", handle_response)

        # Перебираем страницы быстро. wait_until="domcontentloaded" не ждет загрузки рекламы
        for page_type, url in [
            ("signings", "https://puckpedia.com/signings"),
            ("trades", "https://puckpedia.com/trades"),
            ("transactions", "https://puckpedia.com/transactions")
        ]:
            try:
                logger.info(f"Открываем страницу {page_type}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(3)  # Короткая пауза, чтобы внутренний JS сайта успел сделать запрос
            except Exception as e:
                logger.error(f"Не удалось полностью загрузить {page_type}, проверяем что успели поймать: {e}")

        await browser.close()

    # --- АНАЛИЗ ДАННЫХ ---
    
    if captured_data["signings"]:
        items = extract_list(captured_data["signings"])
        if items:
            current_id = str(items[0].get("cid", "") or items[0].get("id", ""))
            logger.info(f"ID последнего подписания: {current_id}")
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
            logger.info(f"ID последнего трейда: {current_id}")
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
            logger.info(f"ID последней транзакции: {current_id}")
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
