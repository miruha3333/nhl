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
    logger.info("Начинаем скрытную проверку обновлений...")
    need_to_run_parser = False
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-dev-shm-usage", 
                "--disable-gpu",
                # Отключаем флаг автоматизации на уровне ключей запуска
                "--disable-blink-features=AutomationControlled"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        # ГЛУБОКАЯ МАСКИРОВКА: Удаляем navigator.webdriver изнутри самого JS-движка
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Блокируем только тяжелые медиа и шрифты. Картинки и CSS оставляем, чтобы Cloudflare не заподозрил неладное
        async def block_heavy_resources(route):
            if route.request.resource_type in ["font", "media"]:
                await route.abort()
            else:
                await route.continue_()
        
        await page.route("**/*", block_heavy_resources)
        
        captured_data = {"signings": None, "trades": None, "transactions": None}
        
        async def handle_response(response):
            url = response.url
            if "api_signings" in url or "api_trades" in url or "api_transactions" in url:
                logger.info(f"Поймали внутренний запрос: {url[:60]}... [Статус: {response.status}]")
                if response.status == 200:
                    try:
                        data = await response.json()
                        if "api_signings" in url:
                            captured_data["signings"] = data
                        elif "api_trades" in url:
                            captured_data["trades"] = data
                        elif "api_transactions" in url:
                            captured_data["transactions"] = data
                    except Exception as e:
                        logger.error(f"Ошибка чтения JSON: {e}")

        page.on("response", handle_response)

        for page_type, url in [
            ("signings", "https://puckpedia.com/signings"),
            ("trades", "https://puckpedia.com/trades"),
            ("transactions", "https://puckpedia.com/transactions")
        ]:
            try:
                logger.info(f"Открываем страницу {page_type}...")
                # Возвращаем стандартное ожидание "load", чтобы Cloudflare успел отработать
                await page.goto(url, wait_until="load", timeout=45000)
                
                # Ждем, пока Cloudflare пропустит нас (исчезнет заголовок проверки)
                for _ in range(10):
                    title = await page.title()
                    if "Just a moment" not in title:
                        break
                    await asyncio.sleep(2)
                
                logger.info(f"Успешно зашли. Текущий заголовок: '{await page.title()}'")
                await asyncio.sleep(5)  # Время на загрузку внутренних таблиц сайта
                
            except Exception as e:
                logger.error(f"Не удалось пройти на страницу {page_type}: {e}")

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
