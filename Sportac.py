import asyncio
import os
import re
import subprocess
import requests
import json
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

        # --- СБОР ПОДПИСАНИЙ через Alpine store ---
        # --- СБОР ПОДПИСАНИЙ через Alpine store ---
        print("Загрузка страницы подписаний...")
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=60000)

        # Ждём появления Alpine и загрузки данных — polling каждые 2 секунды, максимум 60 сек
        for attempt in range(30):
            await asyncio.sleep(2)
            result = await page.evaluate('''() => {
                try {
                    if (typeof Alpine === "undefined") return {status: "no_alpine", count: 0};
                    const store = Alpine.store("puck_filters");
                    if (!store) return {status: "no_store", count: 0};
                    const data = store.puckdata;
                    if (!Array.isArray(data)) return {status: "no_array", count: 0};
                    return {status: "ok", count: data.length};
                } catch(e) {
                    return {status: "error", count: 0, msg: e.message};
                }
            }''')
            print(f"  Попытка {attempt + 1}: статус={result['status']}, записей={result['count']}")
            if result['status'] == 'ok' and result['count'] > 0:
                break

        # Вытаскиваем данные прямо из Alpine store
        raw_signings = await page.evaluate('''() => {
            try {
                const data = Alpine.store("puck_filters").puckdata ?? [];
                return data.slice(0, 5).map(x => ({
                    keys: Object.keys(x),
                    p_fn: x.p_fn ?? x.first_name ?? x.fname ?? "",
                    p_ln: x.p_ln ?? x.last_name ?? x.lname ?? "",
                    cap_hit: x.cap_hit ?? x.caphit ?? 0,
                    cval: x.cval ?? 0,
                    len: x.len ?? x.term ?? x.years ?? x.length ?? 1,
                    lvl: x.lvl ?? x.level ?? x.contract_type ?? "",
                    type_name: x.type_name ?? x.signing_type ?? "",
                    sign_team: x.sign_team ?? x.team ?? x.sign_team_name ?? "",
                    sign_city: x.sign_city ?? "",
                    sign_team_name: x.sign_team_name ?? ""
                }));
            } catch(e) {
                return [{error: e.message}];
            }
        }''')

        print(f"Данные из Alpine store: {json.dumps(raw_signings[:2], ensure_ascii=False, indent=2)}")

        for item in raw_signings:
            if 'error' in item:
                print(f"Ошибка store: {item['error']}")
                continue

            p_fn = str(item.get('p_fn', '')).strip()
            p_ln = str(item.get('p_ln', '')).strip()
            if not p_fn and not p_ln:
                continue

            sign_city = str(item.get('sign_city', '')).strip()
            sign_team_name = str(item.get('sign_team_name', '')).strip()
            team_name = f"{sign_city} {sign_team_name}".strip() if sign_city or sign_team_name else str(item.get('sign_team', '')).strip()

            extracted_signings.append({
                'p_fn': p_fn,
                'p_ln': p_ln,
                'team_name': team_name,
                'cval': item.get('cap_hit', 0),
                'len': item.get('len', 1),
                'lvl': str(item.get('lvl', '')).upper(),
                'type_name': str(item.get('type_name', '')).lower()
            })

        print(f"Итого подписаний: {len(extracted_signings)}")

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

    if not extracted_signings:
        print("Подписания не загрузились (Alpine store пустой). Операция прервана без отправки.")
        return

    if not trades:
        print("Трейды не загрузились. Операция прервана без отправки.")
        return

    print(f"Успешно собрано. Подписаний: {len(extracted_signings)}, Трейдов: {len(trades)}")

    # --- ФОРМИРОВАНИЕ ТЕКСТА И КЭШИРОВАНИЕ ---
    s_list = []
    current_signature_elements = []

    for item in extracted_signings[:3]:
        first_name = str(item.get('p_fn', '')).strip()
        last_name = str(item.get('p_ln', '')).strip()
        name = f"{first_name} {last_name}".strip()
        if not name:
            continue

        current_signature_elements.append(name)

        lvl = str(item.get("lvl", "")).upper()
        raw_cval = str(item.get('cval', 0) or 0)
        try:
            cap_val = float(re.sub(r'[^0-9.]', '', raw_cval) or 0) / 10
        except:
            cap_val = 0

        years_raw = str(item.get('len') or '1')
        try:
            years = int(re.sub(r'[^0-9]', '', years_raw) or 1)
        except:
            years = 1

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
