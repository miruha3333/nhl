import asyncio
import os
import re
import subprocess
import requests
from playwright.async_api import async_playwright

CACHE_FILE = "last_data_cache.txt"

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
        
        # Ждём дольше — даём Alpine.js время отрендерить данные
        await asyncio.sleep(8)

        diag_signings = await page.evaluate('''() => {
            const report = [];

            // Проверяем наличие ключевых селекторов
            const checks = [
                'div.font-bold.font-sans.text-lg',
                'div.font-bold.font-sans.text-lg a.pp_link',
                'a.pl-2.text-pp-copy_dk',
                'a.pl-2.text-pp-copy_dk span',
                'a.pp_link',
                'tr[\\:key="x.cid"]',
                'div[x-data]',
                'div.flex-1.mt-3'
            ];

            for (const sel of checks) {
                const els = document.querySelectorAll(sel);
                report.push(`${sel}: найдено ${els.length} элементов`);
                if (els.length > 0 && els.length <= 3) {
                    report.push(`  -> первый текст: "${els[0].innerText?.trim().slice(0, 100)}"`);
                }
            }

            // Дополнительно: ищем любые ссылки на игроков
            const playerLinks = document.querySelectorAll('a[href*="/player/"]');
            report.push(`a[href*="/player/"]: найдено ${playerLinks.length}`);
            if (playerLinks.length > 0) {
                report.push(`  -> первый: "${playerLinks[0].innerText?.trim()}" href="${playerLinks[0].href}"`);
            }

            // Ищем любые span с текстом похожим на имя команды
            const teamLinks = document.querySelectorAll('a[href*="/team/"]');
            report.push(`a[href*="/team/"]: найдено ${teamLinks.length}`);
            if (teamLinks.length > 0) {
                report.push(`  -> первый: "${teamLinks[0].innerText?.trim().slice(0, 80)}"`);
            }

            // Смотрим x-data атрибуты
            const xdata = document.querySelectorAll('[x-data]');
            report.push(`[x-data] элементов: ${xdata.length}`);

            // Смотрим x-text атрибуты
            const xtext = document.querySelectorAll('[x-text]');
            report.push(`[x-text] элементов: ${xtext.length}`);
            if (xtext.length > 0 && xtext.length <= 10) {
                for (const el of xtext) {
                    report.push(`  x-text="${el.getAttribute('x-text')}" -> текст: "${el.innerText?.trim().slice(0, 60)}"`);
                }
            }

            return report;
        }''')

        print("\n".join(diag_signings))

        # Сохраняем кусок HTML для анализа
        html_snippet = await page.evaluate('''() => {
            // Берём первые 3000 символов body для анализа структуры
            return document.body.innerHTML.slice(0, 5000);
        }''')
        print("\n=== ПЕРВЫЕ 5000 СИМВОЛОВ HTML ===")
        print(html_snippet)

        # --- ДИАГНОСТИКА ТРЕЙДОВ ---
        print("\n=== ДИАГНОСТИКА ТРЕЙДОВ ===")
        await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        diag_trades = await page.evaluate('''() => {
            const report = [];

            const checks = [
                'div[x-html="row.details_nolinks"]',
                'div[x-html]',
                '[x-html]',
                'div[x-data]',
                'a[href*="/trade/"]'
            ];

            for (const sel of checks) {
                const els = document.querySelectorAll(sel);
                report.push(`${sel}: найдено ${els.length}`);
                if (els.length > 0 && els.length <= 3) {
                    report.push(`  -> первый текст: "${els[0].innerText?.trim().slice(0, 150)}"`);
                    report.push(`  -> атрибут x-html: "${els[0].getAttribute('x-html')}"`);
                }
            }

            return report;
        }''')

        print("\n".join(diag_trades))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
