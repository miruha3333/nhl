import os
import asyncio
from playwright.async_api import async_playwright

# --- КОНФИГУРАЦИЯ ---
TEAM_MAPPING = {
    'utah': 'UTAH', 'mammoth': 'UTAH', 'blue jackets': 'CBJ', 'bluejackets': 'CBJ',
    'predators': 'NAS', 'ducks': 'ANA', 'jets': 'WPG', 'wild': 'MIN', 'islanders': 'NYI',
    'rangers': 'NYR', 'kings': 'LAK', 'sabres': 'BUF', 'blackhawks': 'CHI', 'golden knights': 'VGK',
    'canucks': 'VAN', 'flyers': 'PHI', 'bruins': 'BOS', 'sharks': 'SJS', 'hurricanes': 'CAR',
    'penguins': 'PIT', 'capitals': 'WSH', 'canadiens': 'MTL', 'senators': 'OTT', 'red wings': 'DET',
    'redwings': 'DET', 'maple leafs': 'TOR', 'mapleleafs': 'TOR', 'oilers': 'EDM', 'panthers': 'FLA',
    'lightning': 'TBL', 'stars': 'DAL', 'avalanche': 'COL', 'devils': 'NJD', 'kraken': 'SEA',
    'flames': 'CGY', 'blues': 'STL'
}

def send_to_telegram(text):
    import requests
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text})

async def main():
    print("Запуск браузера для обхода защиты...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Важно: используем реальный user_agent
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        # Переход на страницу
        await page.goto("https://puckpedia.com/signings", wait_until="networkidle")
        
        # Ждем немного, чтобы Cloudflare "поверил", что мы человек
        await asyncio.sleep(10)
        
        # Получаем данные прямо из элементов страницы
        print("Сбор данных...")
        # Используем JS для получения данных, так как API может быть защищено
        data = await page.evaluate("() => document.body.innerText")
        
        await browser.close()
        
        if "Just a moment" in data:
            print("DEBUG: Не удалось обойти защиту Cloudflare!")
            return

        msg = "Парсер сработал успешно! Данные получены."
        send_to_telegram(msg)
        print("Сообщение отправлено!")

if __name__ == "__main__":
    asyncio.run(main())
