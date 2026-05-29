import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # --- ДИАГНОСТИКА ПОДПИСАНИЙ ---
        print("=== ДИАГНОСТИКА ПОДПИСАНИЙ ===")
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        diag_signings = await page.evaluate('''() => {
            const report = [];

            const checks = [
                'div.font-bold',
                'a.pp_link',
                'a[href*="/player/"]',
                'a[href*="/team/"]',
                'a.pl-2',
                'div[x-data]',
                'span[x-text]',
                '[x-text]',
                '[x-html]',
                'div.flex-1'
            ];

            for (const sel of checks) {
                try {
                    const els = document.querySelectorAll(sel);
                    report.push(sel + ": найдено " + els.length);
                    if (els.length > 0 && els.length <= 5) {
                        report.push("  -> первый текст: " + (els[0].innerText || "").trim().slice(0, 120));
                    }
                } catch(e) {
                    report.push(sel + ": ОШИБКА СЕЛЕКТОРА - " + e.message);
                }
            }

            const playerLinks = document.querySelectorAll('a[href*="/player/"]');
            if (playerLinks.length > 0) {
                report.push("Примеры ссылок на игроков:");
                for (let i = 0; i < Math.min(3, playerLinks.length); i++) {
                    report.push("  " + playerLinks[i].innerText.trim() + " -> " + playerLinks[i].href);
                }
            }

            const teamLinks = document.querySelectorAll('a[href*="/team/"]');
            if (teamLinks.length > 0) {
                report.push("Примеры ссылок на команды:");
                for (let i = 0; i < Math.min(3, teamLinks.length); i++) {
                    report.push("  " + teamLinks[i].innerText.trim().slice(0, 80) + " -> " + teamLinks[i].href);
                }
            }

            const xtextEls = document.querySelectorAll('[x-text]');
            if (xtextEls.length > 0) {
                report.push("x-text атрибуты (первые 10):");
                for (let i = 0; i < Math.min(10, xtextEls.length); i++) {
                    const attr = xtextEls[i].getAttribute('x-text');
                    const text = (xtextEls[i].innerText || "").trim().slice(0, 60);
                    report.push("  x-text='" + attr + "' -> '" + text + "'");
                }
            }

            return report;
        }''')

        print("\n".join(diag_signings))

        print("\n=== ПЕРВЫЕ 5000 СИМВОЛОВ HTML (ПОДПИСАНИЯ) ===")
        html_signings = await page.evaluate('() => document.body.innerHTML.slice(0, 5000)')
        print(html_signings)

        # --- ДИАГНОСТИКА ТРЕЙДОВ ---
        print("\n=== ДИАГНОСТИКА ТРЕЙДОВ ===")
        await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        diag_trades = await page.evaluate('''() => {
            const report = [];

            const checks = [
                '[x-html]',
                'div[x-html]',
                'a[href*="/trade/"]',
                'div[x-data]',
                '[x-text]'
            ];

            for (const sel of checks) {
                try {
                    const els = document.querySelectorAll(sel);
                    report.push(sel + ": найдено " + els.length);
                    if (els.length > 0 && els.length <= 3) {
                        report.push("  -> текст: " + (els[0].innerText || "").trim().slice(0, 150));
                        const xh = els[0].getAttribute('x-html');
                        if (xh) report.push("  -> x-html атрибут: " + xh);
                    }
                } catch(e) {
                    report.push(sel + ": ОШИБКА - " + e.message);
                }
            }

            return report;
        }''')

        print("\n".join(diag_trades))

        print("\n=== ПЕРВЫЕ 5000 СИМВОЛОВ HTML (ТРЕЙДЫ) ===")
        html_trades = await page.evaluate('() => document.body.innerHTML.slice(0, 5000)')
        print(html_trades)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
