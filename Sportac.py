import asyncio
import os
import re
import json
import subprocess
import requests
from playwright.async_api import async_playwright

# --- НАСТРОЙКИ ---

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

RUS_TEAM_MAPPING = {
    'Buffalo Sabres': {'main': 'Баффало обменяли', 'from': 'из Баффало'},
    'Carolina Hurricanes': {'main': 'Каролина обменяла', 'from': 'из Каролины'},
    'Boston Bruins': {'main': 'Бостон обменял', 'from': 'из Бостона'},
    'Columbus Blue Jackets': {'main': 'Коламбус обменял', 'from': 'из Коламбуса'},
    'Detroit Red Wings': {'main': 'Детройт обменял', 'from': 'из Детройта'},
    'New Jersey Devils': {'main': 'Нью-Джерси обменяли', 'from': 'из Нью-Джерси'},
    'Montreal Canadiens': {'main': 'Монреаль обменял', 'from': 'из Монреаля'},
    'New York Islanders': {'main': 'Айлендерс обменял', 'from': 'из Айлендерс'},
    'Ottawa Senators': {'main': 'Оттава обменяла', 'from': 'из Оттавы'},
    'New York Rangers': {'main': 'Рейнджерс обменяли', 'from': 'из Рейнджерс'},
    'Tampa Bay Lightning': {'main': 'Тампа обменяла', 'from': 'из Тампы'},
    'Philadelphia Flyers': {'main': 'Филадельфия обменяла', 'from': 'из Филадельфии'},
    'Toronto Maple Leafs': {'main': 'Торонто обменяло', 'from': 'из Торонто'},
    'Pittsburgh Penguins': {'main': 'Питтсбург обменял', 'from': 'из Питтсбурга'},
    'Florida Panthers': {'main': 'Флорида обменяла', 'from': 'из Флориды'},
    'Washington Capitals': {'main': 'Вашингтон обменял', 'from': 'из Вашингтона'},
    'Chicago Blackhawks': {'main': 'Чикаго обменяло', 'from': 'из Чикаго'},
    'Anaheim Ducks': {'main': 'Анахайм обменял', 'from': 'из Анахайма'},
    'Colorado Avalanche': {'main': 'Колорадо обменяло', 'from': 'из Колорадо'},
    'Calgary Flames': {'main': 'Калгари обменяли', 'from': 'из Калгари'},
    'Dallas Stars': {'main': 'Даллас обменял', 'from': 'из Далласа'},
    'Edmonton Oilers': {'main': 'Эдмонтон обменял', 'from': 'из Эдмонтона'},
    'Minnesota Wild': {'main': 'Миннесота обменяла', 'from': 'из Миннесоты'},
    'Los Angeles Kings': {'main': 'Лос-Анджелес обменял', 'from': 'из Лос-Анджелеса'},
    'Nashville Predators': {'main': 'Нэшвилл обменял', 'from': 'из Нэшвилла'},
    'San Jose Sharks': {'main': 'Сан-Хосе обменяло', 'from': 'из Сан-Хосе'},
    'St. Louis Blues': {'main': 'Сент-Луис обменял', 'from': 'из Сент-Луиса'},
    'Seattle Kraken': {'main': 'Сиэттл обменял', 'from': 'из Сиэттла'},
    'Utah Mammoth': {'main': 'Юта обменяла', 'from': 'из Юты'},
    'Vancouver Canucks': {'main': 'Ванкувер обменял', 'from': 'из Ванкувера'},
    'Winnipeg Jets': {'main': 'Виннипег обменял', 'from': 'из Виннипега'}
}

CACHE_FILE = "last_data_cache.txt"

def get_last_cached_signature():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_to_cache_and_commit(new_signature):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(new_signature)

    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", CACHE_FILE], check=True)
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", "Обновление кэша последних событий [skip ci]"], check=True)
                subprocess.run(["git", "push"], check=True)
                print("Кэш успешно сохранен в репозиторий GitHub.")
        except Exception as e:
            print(f"Не удалось сохранить кэш в Git: {e}")

def get_rus_team_data(eng_name):
    clean_name = eng_name.strip()
    for key, value in RUS_TEAM_MAPPING.items():
        if clean_name.lower() in key.lower():
            return value
    return {'main': f"{clean_name} обменял", 'from': f"из {clean_name}"}

def send_to_telegram(text):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    max_len = 3500
    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for part in parts:
        try:
            requests.post(url, data={"chat_id": chat_id, "text": part}, timeout=15)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

def get_team_abbr(team_name_raw):
    if not team_name_raw:
        return ""
    clean_name = re.sub(r'<[^>]+>', '', str(team_name_raw)).lower().strip()
    for team_key, abbr in TEAM_MAPPING.items():
        if team_key in clean_name:
            return f"({abbr})"
    return f"({clean_name[:3].upper()})"

def format_years(years_raw):
    try:
        years = int(re.sub(r'[^0-9]', '', str(years_raw)))
    except:
        return "на срок"
    if years == 1:
        return "на 1 год"
    elif 2 <= years <= 4:
        return f"на {years} года"
    else:
        return f"на {years} лет"

def format_cap_hit(val_raw):
    try:
        clean_val = int(re.sub(r'[^0-9]', '', str(val_raw)))
        return f"{clean_val:,}"
    except:
        return f"{val_raw}"

def translate_trade(text):
    if "forfeit" in text.lower():
        return text
    pattern = r"The (.+?) acquire (.+?) from the (.+?) for (.+)"
    match = re.search(pattern, text)
    if match:
        team1, p1, team2, p2 = match.groups()
        rus_team1_data = get_rus_team_data(team1)
        rus_team2_data = get_rus_team_data(team2)

        p1 = p1.replace(".", "").replace(" and ", " и ")
        p2 = p2.replace(".", "").replace(" and ", " и ")

        return f"{rus_team1_data['main']} {p2} на {p1} {rus_team2_data['from']}"
    return text

async def main():
    extracted_signings = []
    trades = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # --- СБОР ПОДПИСАНИЙ ---
        print("Загрузка страницы подписаний...")
        try:
            await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=60000)

            # Ждём появления динамически подгружаемых карточек игроков
            await page.wait_for_selector(
                'div.flex-1.mt-3.grid.grid-cols-3',
                timeout=30000
            )
        except Exception as e:
            print(f"Предупреждение по подписаниям: {e}")

        # Собираем данные из динамических карточек игроков
        extracted_signings = await page.evaluate('''() => {
            const results = [];

            // Ищем все строки-карточки подписаний
            // Каждая карточка игрока содержит блок с деталями контракта
            const playerCards = Array.from(document.querySelectorAll(
                'div.flex-1.mt-3, div[class*="flex-1"][class*="mt-3"][class*="grid-cols-3"]'
            ));

            for (const card of playerCards) {
                try {
                    // Поднимаемся к родительскому блоку всей строки подписания
                    const row = card.closest('[class*="border-b"], [class*="py-"], li, article') || card.parentElement;

                    // Имя игрока — ищем ближайшую ссылку или заголовок рядом с карточкой
                    const nameEl = row?.querySelector('a[href*="/player/"], span.font-bold, h2, h3')
                        || card.previousElementSibling?.querySelector('a, span')
                        || card.parentElement?.previousElementSibling?.querySelector('a, span');
                    const fullName = nameEl?.innerText?.trim() || '';
                    if (!fullName) continue;

                    const nameParts = fullName.split(' ');
                    const p_fn = nameParts[0] || '';
                    const p_ln = nameParts.slice(1).join(' ') || '';

                    // Все текстовые блоки внутри карточки деталей
                    const spans = Array.from(card.querySelectorAll('span, div'));
                    const texts = spans.map(el => el.innerText?.trim()).filter(Boolean);

                    // Команда — ищем рядом с карточкой
                    const teamEl = row?.querySelector('img[alt], [class*="team"], a[href*="/team/"]');
                    const team_name = teamEl?.getAttribute('alt') || teamEl?.innerText?.trim() || '';

                    // Пытаемся найти кэпхит, длину и уровень среди текстов
                    let cval = '0', len = '1', lvl = '', type_name = '';

                    for (const t of texts) {
                        // Кэпхит: содержит $ или выглядит как число с суффиксом M/K
                        if (/\$[\d,]+|\d+[\.,]\d+\s*[MmKk]/.test(t)) {
                            cval = t.replace(/[^0-9.]/g, '') || '0';
                        }
                        // Длина контракта: число + yr/year
                        if (/^\d+\s*(yr|year)/i.test(t)) {
                            len = t.replace(/[^0-9]/g, '') || '1';
                        }
                        // Уровень: ELC, UFA, RFA и т.д.
                        if (/^(ELC|UFA|RFA|PTO|AHL|NHL)$/i.test(t)) {
                            lvl = t.toUpperCase();
                        }
                        // Тип: Extension
                        if (/extension/i.test(t)) {
                            type_name = t;
                        }
                    }

                    results.push({ p_fn, p_ln, team_name, cval, len, lvl, type_name });

                    if (results.length >= 5) break;
                } catch (err) {
                    // пропускаем сломанные карточки
                }
            }

            return results;
        }''')

        print(f"Найдено подписаний через flex-карточки: {len(extracted_signings)}")

        # Запасной вариант: если карточки не дали результат,
        # пробуем найти данные через Alpine.js x-data или window.__data
        if not extracted_signings:
            print("Пробуем альтернативный способ сбора подписаний через JS-состояние...")
            extracted_signings = await page.evaluate('''() => {
                const results = [];

                // Пытаемся найти Alpine.js компоненты с данными подписаний
                const alpineEls = Array.from(document.querySelectorAll('[x-data]'));
                for (const el of alpineEls) {
                    try {
                        const data = el._x_dataStack?.[0] || {};
                        const items = data.signings || data.items || data.data || data.rows || [];
                        if (Array.isArray(items) && items.length > 0) {
                            for (const item of items.slice(0, 5)) {
                                results.push({
                                    p_fn: item.p_fn || item.first_name || '',
                                    p_ln: item.p_ln || item.last_name || '',
                                    team_name: item.team_name || item.team || '',
                                    cval: String(item.cval || item.cap_hit || item.value || '0'),
                                    len: String(item.len || item.years || item.length || '1'),
                                    lvl: item.lvl || item.level || item.type || '',
                                    type_name: item.type_name || ''
                                });
                            }
                            if (results.length > 0) break;
                        }
                    } catch(e) {}
                }

                // Если Alpine не помог — пробуем найти данные в глобальных переменных окна
                if (results.length === 0) {
                    const candidates = ['signings', 'transactions', 'data', 'pageData', 'appData'];
                    for (const key of candidates) {
                        try {
                            const val = window[key];
                            if (Array.isArray(val) && val.length > 0 && val[0].p_fn !== undefined) {
                                for (const item of val.slice(0, 5)) {
                                    results.push({
                                        p_fn: item.p_fn || '',
                                        p_ln: item.p_ln || '',
                                        team_name: item.team_name || '',
                                        cval: String(item.cval || '0'),
                                        len: String(item.len || '1'),
                                        lvl: item.lvl || '',
                                        type_name: item.type_name || ''
                                    });
                                }
                                break;
                            }
                        } catch(e) {}
                    }
                }

                return results;
            }''')
            print(f"Найдено подписаний через JS-состояние: {len(extracted_signings)}")

        # --- СБОР ТРЕЙДОВ ---
        print("Загрузка страницы трейдов...")
        try:
            await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_selector('div[x-html="row.details_nolinks"]', timeout=20000)
        except Exception as e:
            print(f"Предупреждение по трейдам: {e}")

        all_trades = await page.evaluate('''() => {
            const blocks = Array.from(document.querySelectorAll('div[x-html="row.details_nolinks"]'));
            return blocks.map(el => el.innerText.trim());
        }''')

        trades = [translate_trade(t) for t in all_trades if "The ID of this channel" not in t and len(t) > 20]

        await browser.close()

    if not extracted_signings and not trades:
        print("Внимание: Никакие данные не собрались. Операция прервана.")
        return

    print(f"Успешно собрано. Подписаний: {len(extracted_signings)}, Трейдов: {len(trades)}")

    # --- ФОРМИРОВАНИЕ ТЕКСТА И КЭШИРОВАНИЕ ---
    s_list = []
    current_signature_elements = []

    for item in extracted_signings[:3]:
        first_name = re.sub(r'<[^>]+>', '', str(item.get('p_fn', ''))).strip()
        last_name = re.sub(r'<[^>]+>', '', str(item.get('p_ln', ''))).strip()
        name = f"{first_name} {last_name}".strip()
        if not name:
            continue

        current_signature_elements.append(name)

        lvl = str(item.get("lvl", "")).upper()
        raw_cval = str(item.get('cval', 0) or 0)
        try:
            total_val = float(re.sub(r'[^0-9.]', '', raw_cval) or 0)
        except:
            total_val = 0

        years = int(str(item.get('len') or 1).replace('на', '').strip() or 1)
        cap_val = total_val / years if "ELC" in lvl else total_val

        raw_type = str(item.get('type_name', '')).lower()
        if "extension" in raw_type or "продл" in raw_type:
            ctype = "продлил контракт"
        else:
            ctype = "подписал контракт новичка" if "ELC" in lvl else "подписал контракт"

        line = f"{name} {ctype} {format_years(years)} с кэпхитом {format_cap_hit(cap_val)} {get_team_abbr(item.get('team_name'))}"
        s_list.append(line)

    seen = set()
    unique_trades = []
    for t in trades:
        if t not in seen:
            seen.add(t)
            unique_trades.append(t)

    t_list = unique_trades[:3]
    for t in t_list:
        current_signature_elements.append(t[:50])

    current_signature = "|".join(current_signature_elements)
    last_cached_signature = get_last_cached_signature()

    if current_signature == last_cached_signature:
        print("Новых событий на PuckPedia нет. Скрипт завершен без отправки дубликатов.")
        return

    message = f"🔥 3 ПОСЛЕДНИХ ПОДПИСАНИЯ:\n\n{chr(10).join([s + chr(10) for s in s_list])}\n🤝 3 ПОСЛЕДНИХ ТРЕЙДА:\n\n{chr(10).join([t + chr(10) for t in t_list])}"

    send_to_telegram(message)
    save_to_cache_and_commit(current_signature)

if __name__ == "__main__":
    asyncio.run(main())
