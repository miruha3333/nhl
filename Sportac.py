import asyncio
import os
import re
import subprocess
import requests
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Перехватываем все сетевые запросы и ответы
        api_responses = []

        async def handle_response(response):
            url = response.url
            # Ищем запросы похожие на API с данными подписаний/трейдов
            if any(k in url for k in ['signing', 'trade', 'transaction', 'api', 'json', 'data', 'puck']):
                try:
                    ct = response.headers.get('content-type', '')
                    if 'json' in ct or 'javascript' in ct:
                        body = await response.text()
                        api_responses.append({
                            'url': url,
                            'status': response.status,
                            'body_preview': body[:500]
                        })
                except:
                    pass

        page.on("response", handle_response)

        print("=== ПЕРЕХВАТ ЗАПРОСОВ: ПОДПИСАНИЯ ===")
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(10)

        print(f"Перехвачено API-запросов: {len(api_responses)}")
        for r in api_responses:
            print(f"\nURL: {r['url']}")
            print(f"Status: {r['status']}")
            print(f"Body: {r['body_preview']}")

        # Сброс для трейдов
        api_responses.clear()

        print("\n=== ПЕРЕХВАТ ЗАПРОСОВ: ТРЕЙДЫ ===")
        await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(10)

        print(f"Перехвачено API-запросов: {len(api_responses)}")
        for r in api_responses:
            print(f"\nURL: {r['url']}")
            print(f"Status: {r['status']}")
            print(f"Body: {r['body_preview']}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
