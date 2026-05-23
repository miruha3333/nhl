import asyncio
import re
import os
import requests
from playwright.async_api import async_playwright

def send_to_telegram(text):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id:
        print("Ошибка: Токены отсутствуют")
        return
    
    # Разбиваем текст, если он превышает лимиты Telegram
    max_len = 3500
    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for part in parts:
        try:
            r = requests.post(url, data={"chat_id": chat_id, "text": part}, timeout=15)
            if r.status_code == 200:
                print("Успешно отправлено!")
            else:
                print(f"Ошибка API: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"Ошибка соединения: {e}")

async def main():
    signings = []
    trades = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()

        # Слушаем API подписаний
        async def on_response(response):
            if "api_signings" in response.url:
                try:
                    data = await response.json()
                    if isinstance(data, dict):
                        key = "rows" if "rows" in data else "p"
                        signings.extend(data.get(key, []))
                except: pass

        page.on("response", on_response)
        
        # Сбор данных
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded")
        await asyncio.sleep(15) 

        await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded")
        await asyncio.sleep(15)
        
        # Получаем трейды и фильтруем мусор
        all_trades = await page.evaluate("""() => Array.from(document.querySelectorAll('[x-html="row.details_nolinks"]')).map(el => el.innerText.trim())""")
        trades = [t for t in all_trades if "The ID of this channel" not in t and len(t) > 20]
        
        await browser.close()

    # --- ФОРМИРОВАНИЕ ИТОГОВОГО ТЕКСТА ---
    
    # Последние 3 подписания
    s_list = []
    if signings:
        for i in signings[:3]:
            name = f"{i.get('p_fn', '')} {i.get('p_ln', '')}".strip()
            team = i.get('team_name', 'Без команды')
            s_list.append(f"• {name} - {team}")
    s_text = "\n".join(s_list) if s_list else "Нет новых подписаний"

    # Последние 3 трейда
    t_text = "\n".join([f"• {t}" for t in trades[:3]]) if trades else "Нет новых трейдов"
    
    message = f"🔥 3 ПОСЛЕДНИХ ПОДПИСАНИЯ:\n{s_text}\n\n🤝 3 ПОСЛЕДНИХ ТРЕЙДА:\n{t_text}"
    
    send_to_telegram(message)

if __name__ == "__main__":
    asyncio.run(main())
