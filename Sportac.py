import os
import asyncio
import requests
from playwright.async_api import async_playwright

# --- ФУНКЦИЯ ОТПРАВКИ В ТЕЛЕГРАМ ---
def send_to_telegram(text):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id:
        print("Ошибка: Токены не заданы!")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, data=payload)
    print(f"Статус отправки: {response.status_code}")

# --- ОСНОВНАЯ ЛОГИКА ---
async def main():
    print("Запуск браузера в режиме эмуляции человека...")
    
    async with async_playwright() as p:
        # Запускаем браузер с параметрами, которые маскируют нас под реального пользователя
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()
        
        # Переходим на страницу
        print("Переход на сайт PuckPedia...")
        try:
            await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=60000)
            # Даем время на выполнение JS-кода защиты Cloudflare
            await asyncio.sleep(20)
            
            # Проверяем, не попали ли мы на страницу проверки
            content = await page.content()
            if "Just a moment" in content:
                print("DEBUG: Защита Cloudflare не пройдена.")
                await browser.close()
                return

            print("Данные успешно прогружены.")
            
            # Извлекаем текст
            page_text = await page.evaluate("() => document.body.innerText")
            
            # Если текст пустой или очень короткий
            if len(page_text) < 500:
                print("DEBUG: Текст страницы слишком короткий.")
            else:
                print("Данные собраны, отправка...")
                send_to_telegram("Парсер успешно получил данные с PuckPedia!")
                
        except Exception as e:
            print(f"Произошла ошибка: {e}")
        
        finally:
            await browser.close()
            print("Работа завершена.")

if __name__ == "__main__":
    asyncio.run(main())
