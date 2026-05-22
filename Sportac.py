import os
import asyncio
import requests
from playwright.async_api import async_playwright

def send_to_telegram(text):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Отправляем сообщение
    response = requests.post(url, data={"chat_id": chat_id, "text": text})
    
    if response.status_code == 200:
        print("Успешно отправлено!")
    else:
        print(f"Ошибка отправки (статус {response.status_code}): {response.text}")

async def main():
    print("Запуск браузера...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(15) 
            
            # Собираем данные: ищем все элементы, похожие на подписания
            # Используем специфический селектор, который PuckPedia использует для строк таблицы
            items = await page.evaluate("""() => {
                let rows = Array.from(document.querySelectorAll('.views-row'));
                return rows.slice(0, 5).map(row => row.innerText.trim());
            }""")
            
            if items:
                msg = "🔥 Последние 5 подписаний:\n\n" + "\n\n".join(items)
                print("Данные собраны, отправляем...")
                send_to_telegram(msg)
            else:
                print("DEBUG: Не удалось найти блоки с подписаниями.")
                
        except Exception as e:
            print(f"Ошибка при работе: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
