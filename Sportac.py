import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        all_responses = []

        async def handle_response(response):
            url = response.url
            ct = response.headers.get('content-type', '')
            if 'json' in ct:
                try:
                    body = await response.text()
                    all_responses.append({
                        'url': url,
                        'status': response.status,
                        'body_preview': body[:1000]
                    })
                except:
                    pass

        page.on("response", handle_response)

        print("=== ПЕРЕХВАТ JSON: ПОДПИСАНИЯ ===")
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=60000)
        # Ждём 15 секунд — даём Alpine время сделать свои запросы
        await asyncio.sleep(15)

        print(f"Найдено JSON-ответов: {len(all_responses)}")
        for r in all_responses:
            print(f"\nURL: {r['url']}")
            print(f"Body: {r['body_preview']}")

        # Смотрим Alpine store
        print("\n=== ALPINE STORE ===")
        store_data = await page.evaluate('''() => {
            try {
                const store = Alpine.store("puck_filters");
                return JSON.stringify(store, null, 2).slice(0, 3000);
            } catch(e) {
                return "Alpine.store недоступен: " + e.message;
            }
        }''')
        print(store_data)

        # Смотрим window объекты с данными
        print("\n=== WINDOW ПЕРЕМЕННЫЕ С ДАННЫМИ ===")
        win_data = await page.evaluate('''() => {
            const results = [];
            const keys = Object.keys(window);
            for (const k of keys) {
                try {
                    const val = window[k];
                    if (val && typeof val === "object" && !Array.isArray(val)) {
                        const str = JSON.stringify(val).slice(0, 200);
                        if (str.includes("signing") || str.includes("player") || str.includes("cap") || str.includes("contract")) {
                            results.push(k + ": " + str);
                        }
                    }
                    if (Array.isArray(val) && val.length > 0) {
                        const str = JSON.stringify(val[0]).slice(0, 200);
                        if (str.includes("signing") || str.includes("player") || str.includes("cap") || str.includes("contract")) {
                            results.push(k + " (array): " + str);
                        }
                    }
                } catch(e) {}
            }
            return results.slice(0, 20);
        }''')
        print("\n".join(win_data) if win_data else "Ничего не найдено")

        # Ищем в HTML скрытые данные (inline JSON в script тегах)
        print("\n=== SCRIPT ТЕГИ С ДАННЫМИ ===")
        script_data = await page.evaluate('''() => {
            const results = [];
            const scripts = document.querySelectorAll("script:not([src])");
            for (const s of scripts) {
                const t = s.textContent || "";
                if (t.includes("signing") || t.includes("p_fn") || t.includes("cap_hit") || t.includes("cval")) {
                    results.push(t.slice(0, 800));
                }
            }
            return results;
        }''')
        if script_data:
            for s in script_data:
                print(s)
                print("---")
        else:
            print("Ничего не найдено")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
