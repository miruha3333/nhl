import os
import re
import json
import logging
import asyncio
from fastapi import FastAPI, BackgroundTasks
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

CACHE_FILE = "last_data_cache.json"
TRANSACTIONS_CACHE_FILE = "transactions_cache.json"

# Читаем настройки GitHub из окружения
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # формат: "username/repo"
GITHUB_WORKFLOW = os.environ.get("GITHUB_WORKFLOW", "main.yml")  # имя файла воркфлоу

async def trigger_github_action():
    """Отправляет запрос на GitHub Actions для запуска основного парсера"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        logger.error("Не настроены переменные GITHUB_TOKEN или GITHUB_REPO. Запуск невозможен.")
        return
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {"ref": "main"}  # или твоя ветка по умолчанию
    
    async with AsyncSession() as session:
        try:
            logger.info("Отправляем сигнал на запуск воркфлоу в GitHub Actions...")
            res = await session.post(url, headers=headers, json=data)
            if res.status_code == 204:
                logger.info("GitHub Actions успешно запущен! Парсер начал работу на стороне GitHub.")
            else:
                logger.error(f"Не удалось запустить GitHub Actions. Статус: {res.status_code}, Ответ: {res.text}")
        except Exception as e:
            logger.error(f"Ошибка при отправке запроса к GitHub API: {e}")

async def async_check():
    logger.info("Начинаем проверку обновлений через анализ HTML страниц...")
    need_to_run_parser = False
    
    pages = {
        "signings": "https://puckpedia.com/signings",
        "trades": "https://puckpedia.com/trades",
        "transactions": "https://puckpedia.com/transactions"
    }
    
    captured_ids = {"signings": None, "trades": None, "transactions": None}
    
    async with AsyncSession() as session:
        for key, url in pages.items():
            logger.info(f"Запрашиваем страницу {url}...")
            try:
                response = await session.get(
                    url, 
                    impersonate="chrome120", 
                    headers={"Accept": "text/html"},
                    timeout=20
                )
                if response.status_code == 200:
                    html_text = response.text
                    
                    # Ищем ID в HTML коде (они зашиты в атрибутах или в JSON конфигурации на странице)
                    if key == "signings":
                        match = re.search(r'"cid":\s*"?(\d+)"?', html_text) or re.search(r'data-id="(\d+)"', html_text)
                    elif key == "trades":
                        match = re.search(r'"trade_id":\s*"?(\d+)"?', html_text) or re.search(r'trade-id="(\d+)"', html_text)
                    else:
                        match = re.search(r'"transaction_id":\s*"?(\d+)"?', html_text) or re.search(r'transaction-id="(\d+)"', html_text)
                    
                    if match:
                        captured_ids[key] = match.group(1)
                        logger.info(f"Найден свежий ID для {key}: {captured_ids[key]}")
                    else:
                        # Если регулярка не сработала, попробуем поискать любой первый попавшийся ID в структурах данных
                        fallback = re.search(r'"id":\s*"?(\d+)"?', html_text)
                        if fallback:
                            captured_ids[key] = fallback.group(1)
                            logger.info(f"Фолбэк: найден ID для {key}: {captured_ids[key]}")
                        else:
                            logger.warning(f"Не удалось вытащить ID со страницы {key}, хотя она загрузилась.")
                else:
                    logger.error(f"Cloudflare заблокировал страницу {key}. Статус: {response.status_code}")
            except Exception as e:
                logger.error(f"Ошибка при обработке страницы {key}: {e}")
            
            await asyncio.sleep(2)

    # --- АНАЛИЗ КЭША ---
    if captured_ids["signings"]:
        cache = {}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        if captured_ids["signings"] != cache.get("signings", {}).get("last_id", ""):
            logger.info("Обнаружены новые подписания!")
            need_to_run_parser = True

    if captured_ids["trades"]:
        cache = {}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        if captured_ids["trades"] != cache.get("trades", {}).get("last_id", ""):
            logger.info("Обнаружены новые трейды!")
            need_to_run_parser = True

    if captured_ids["transactions"]:
        tx_cache = {}
        if os.path.exists(TRANSACTIONS_CACHE_FILE):
            with open(TRANSACTIONS_CACHE_FILE, "r", encoding="utf-8") as f:
                tx_cache = json.load(f)
        if captured_ids["transactions"] != tx_cache.get("last_id", ""):
            logger.info("Обнаружены новые транзакции!")
            need_to_run_parser = True

    # --- ИТОГОВОЕ РЕШЕНИЕ ---
    if need_to_run_parser:
        await trigger_github_action()
    else:
        logger.info("Изменений не найдено. Засыпаем.")

def check_for_updates():
    asyncio.run(async_check())

@app.get("/check")
def trigger_check(background_tasks: BackgroundTasks):
    background_tasks.add_task(check_for_updates)
    return {"status": "Checking started"}
