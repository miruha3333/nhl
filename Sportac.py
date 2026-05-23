import asyncio
import re
import os
import requests
from playwright.async_api import async_playwright

def send_to_telegram(text):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Разбиваем текст на части, если он слишком длинный
    max_len = 3500
    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for part in parts:
        requests.post(url, data={"chat_id": chat_id, "text": part}, timeout=15)

async def main():
    signings = []
    trades = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await context.new_page()

        # Собираем подписания (пробуем разные пути, если API изменилось)
        async def on_response(response):
            if "api_signings" in response.url:
                try:
                    data = await response.json()
                    if isinstance(data, dict):
                        # Собираем всё, что похоже на массив данных
                        key = "rows" if "rows" in data else "p"
                        signings.extend(data.get(key, []))
                except: pass
        page.on("response", on_response)
        
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded")
        await asyncio.sleep(15) 

        # Собираем трейды
        await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded")
        await asyncio.sleep(15)
        # Собираем элементы и сразу отсеиваем "мусор" (ID канала и прочее)
        all_trades = await page.evaluate("""() => Array.from(document.querySelectorAll('[x-html="row.details_nolinks"]')).map(el => el.innerText.trim())""")
        trades = [t for t in all_trades if "The ID of this channel" not in t and len(t) > 20]
        
        await browser.close()

    # --- ФОРМИРОВАНИЕ (последние 3) ---
    # Для подписаний берем 3 последних (они обычно в начале списка API)
    s_text = "Нет данных"
    if signings:
        s_list = []
        for i in signings[:3]:
            name = f"{i.get('p_fn', '')} {i.get('p_ln', '')}"
            s_list.append(f"• {name} - {i.get('team_name', '')}")
        s_text = "\n".join(s_list)

    # Для трейдов берем 3 последних
    t_text = "Нет данных"
    if trades:
        t_list = [f"• {t}" for t in trades[:3]]
        t_text = "\n".join(t_list)
    
    message = f"🔥 3 ПОСЛЕДНИХ ПОДПИСАНИЯ:\n{s_text}\n\n🤝 3 ПОСЛЕДНИХ ТРЕЙДА:\n{t_text}"
    send_to_telegram(message)

if __name__ == "__main__":
    asyncio.run(main())
