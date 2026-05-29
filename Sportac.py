import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Перехватываем ВСЕ запросы без фильтра
        all_responses = []

        async def handle_response(response):
            url = response.url
            status = response.status
            ct = response.headers.get('content-type', '')
            # Берём только JSON-ответы и нешаблонные JS
            if 'json' in ct:
                try:
                    body = await response.text()
                    all_responses.append({
                        'url': url,
                        'status': status,
                        'ct': ct,
                        'body_preview': body[:800]
                    })
                except:
                    pass

        page.on("response", handle_response)

        print("=== ПЕРЕХВАТ JSON-ЗАПРОСОВ: ПОДПИСАНИЯ ===")
        await page.goto("https://puckpedia.com/signings", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)

        print(f"Найдено JSON-ответов: {len(all_responses)}")
        for r in all_responses:
            print(f"\nURL: {r['url']}")
            print(f"Body: {r['body_preview']}")

        # Дополнительно — смотрим что лежит в Alpine store
        print("\n=== ALPINE STORE ===")
        store_data = await page.evaluate('''() => {
            try {
                // Alpine v3
                const store = Alpine.store('puck_filters');
                return JSON.stringify(store, null, 2).slice(0, 3000);
            } catch(e) {
                return "Alpine.store недоступен: " + e.message;
            }
        }''')
        print(store_data)

        # Смотрим все x-data компоненты и что в них хранится
        print("\n=== X-DATA КОМПОНЕНТЫ ===")
        xdata_info = await page.evaluate('''() => {
            const results = [];
            const els = document.querySelectorAll('[x-data]');
            for (const el of els) {
                try {
                    const attr = el.getAttribute('x-data');
                    const stack = el._x_dataStack;
                    let dataStr = '';
                    if (stack && stack[0]) {
                        dataStr = JSON.stringify(stack[0], null, 2).slice(0, 500);
                    }
                    results.push('x-data="' + attr.slice(0, 80) + '"');
                    if (dataStr) results.push('  данные: ' + dataStr);
                } catch(e) {
                    results.push('  ошибка: ' + e.message);
                }
            }
            return results;
        }''')
        print("\n".join(xdata_info))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
