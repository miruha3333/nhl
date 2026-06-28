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
    logger.info("Начинаем проверку обновлений через перехватчик сетевых ответов...")
    need_to_run_parser = False
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Словарь для хранения перехваченного JSON по каждому разделу
        captured_data = {"signings": None, "trades": None, "transactions": None}
        
        # Функция-слушатель: ловит ответы от сервера самой PuckPedia
        async def handle_response(response):
            url = response.url
            if response.status == 200:
                try:
                    if "api_signings" in url:
                        captured_data["signings"] = await response.json()
                        logger.info("Успешно перехвачен JSON подписаний.")
                    elif "api_trades" in url:
                        captured_data["trades"] = await response.json()
                        logger.info("Успешно перехвачен JSON трейдов.")
                    elif "api_transactions" in url:
                        captured_data["transactions"] = await response.json()
                        logger.info("Успешно перехвачен JSON транзакций.")
                except Exception:
                    pass

        page.on("response", handle_response)

        # 1. Загружаем страницу подписаний
        try:
            logger.info("Открываем страницу подписаний...")
            await page.goto("https://puckpedia.com/signings", wait_until="load", timeout=45000)
            await asyncio.sleep(4)  # Даем время на выполнение внутренних скриптов
        except Exception as e:
            logger.error(f"Не удалось загрузить страницу подписаний: {e}")

        # 2. Загружаем страницу трейдов
        try:
            logger.info("Открываем страницу трейдов...")
            await page.goto("https://puckpedia.com/trades", wait_until="load", timeout=45000)
            await asyncio.sleep(4)
        except Exception as e:
            logger.error(f"Не удалось загрузить страницу трейдов: {e}")

        # 3. Загружаем страницу транзакций
        try:
            logger.info("Открываем страницу транзакций...")
            await page.goto("https://puckpedia.com/transactions", wait_until="load", timeout=45000)
            await asyncio.sleep(4)
        except Exception as e:
            logger.error(f"Не удалось загрузить страницу транзакций: {e}")

        await browser.close()

    # --- АНАЛИЗ ПОЛУЧЕННЫХ ДАННЫХ ---
    
    # 1. Проверка подписаний
    if captured_data["signings"]:
        items = extract_list(captured_data["signings"])
        if items:
            current_id = str(items[0].get("cid", "") or items[0].get("id", ""))
            logger.info(f"Последний ID подписания на сайте: {current_id}")
            cache = {}
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            if current_id != cache.get("signings", {}).get("last_id", ""):
                logger.info("Обнаружены новые подписания!")
                need_to_run_parser = True
    else:
        logger.warning("Данные API подписаний не были получены.")

    # 2. Проверка трейдов
    if captured_data["trades"]:
        items = extract_list(captured_data["trades"])
        if items:
            current_id = str(items[0].get("trade_id", "") or items[0].get("id", ""))
            logger.info(f"Последний ID трейда на сайте: {current_id}")
            cache = {}
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            if current_id != cache.get("trades", {}).get("last_id", ""):
                logger.info("Обнаружены новые трейды!")
                need_to_run_parser = True
    else:
        logger.warning("Данные API трейдов не были получены.")

    # 3. Проверка транзакций
    if captured_data["transactions"]:
        items = extract_list(captured_data["transactions"])
        if items:
            current_id = str(items[0].get("transaction_id", "") or items[0].get("id", ""))
            logger.info(f"Последний ID транзакции на сайте: {current_id}")
            tx_cache = {}
            if os.path.exists(TRANSACTIONS_CACHE_FILE):
                with open(TRANSACTIONS_CACHE_FILE, "r", encoding="utf-8") as f:
                    tx_cache = json.load(f)
            if current_id != tx_cache.get("last_id", ""):
                logger.info("Обнаружены новые транзакции!")
                need_to_run_parser = True
    else:
        logger.warning("Данные API транзакций не были получены.")

    # --- ИТОГОВОЕ РЕШЕНИЕ ---
    if need_to_run_parser:
        logger.info("Активация основного парсера github.py...")
        subprocess.run(["python3", "github.py"])
    else:
        logger.info("Изменений на сайте не найдено. Засыпаем.")

def check_for_updates():
    asyncio.run(async_check())

@app.get("/check")
def trigger_check(background_tasks: BackgroundTasks):
    background_tasks.add_task(check_for_updates)
    return {"status": "Checking started"}
