import asyncio
import os
import re
import subprocess
import requests
import json
from datetime import datetime
from playwright.async_api import async_playwright

# --- НАСТРОЙКИ ---

TEAM_MAPPING_ABBR = {
    'utah': 'UTAH', 'mammoth': 'UTAH', 'blue jackets': 'CBJ', 'bluejackets': 'CBJ',
    'predators': 'NAS', 'ducks': 'ANA', 'jets': 'WPG', 'wild': 'MIN', 'islanders': 'NYI',
    'rangers': 'NYR', 'kings': 'LAK', 'sabres': 'BUF', 'blackhawks': 'CHI', 'golden knights': 'VGK',
    'canucks': 'VAN', 'flyers': 'PHI', 'bruins': 'BOS', 'sharks': 'SJS', 'hurricanes': 'CAR',
    'penguins': 'PIT', 'capitals': 'WSH', 'canadiens': 'MTL', 'senators': 'OTT', 'red wings': 'DET',
    'redwings': 'DET', 'maple leafs': 'TOR', 'mapleleafs': 'TOR', 'oilers': 'EDM', 'panthers': 'FLA',
    'lightning': 'TBL', 'stars': 'DAL', 'avalanche': 'COL', 'devils': 'NJD', 'kraken': 'SEA',
    'flames': 'CGY', 'blues': 'STL'
}

TEAM_MAPPING_SLUG = {
    'utah': 'UTAH', 'mammoth': 'UTAH', 'utah-mammoth': 'UTAH', 'columbus-blue-jackets': 'CBJ',
    'nashville-predators': 'NAS', 'anaheim-ducks': 'ANA', 'winnipeg-jets': 'WPG', 'minnesota-wild': 'MIN',
    'new-york-islanders': 'NYI', 'new-york-rangers': 'NYR', 'los-angeles-kings': 'LAK', 'buffalo-sabres': 'BUF',
    'chicago-blackhawks': 'CHI', 'vegas-golden-knights': 'VGK', 'vancouver-canucks': 'VAN',
    'philadelphia-flyers': 'PHI', 'boston-bruins': 'BOS', 'san-jose-sharks': 'SJS',
    'carolina-hurricanes': 'CAR', 'pittsburgh-penguins': 'PIT', 'washington-capitals': 'WSH',
    'montreal-canadiens': 'MTL', 'ottawa-senators': 'OTT', 'detroit-red-wings': 'DET',
    'toronto-maple-leafs': 'TOR', 'edmonton-oilers': 'EDM', 'florida-panthers': 'FLA',
    'tampa-bay-lightning': 'TBL', 'dallas-stars': 'DAL', 'colorado-avalanche': 'COL',
    'new-jersey-devils': 'NJD', 'seattle-kraken': 'SEA', 'calgary-flames': 'CGY', 'st-louis-blues': 'STL',
    'blue-jackets': 'CBJ', 'predators': 'NAS', 'ducks': 'ANA', 'jets': 'WPG', 'wild': 'MIN',
    'islanders': 'NYI', 'rangers': 'NYR', 'kings': 'LAK', 'sabres': 'BUF', 'blackhawks': 'CHI',
    'golden-knights': 'VGK', 'canucks': 'VAN', 'flyers': 'PHI', 'bruins': 'BOS', 'sharks': 'SJS',
    'hurricanes': 'CAR', 'penguins': 'PIT', 'capitals': 'WSH', 'canadiens': 'MTL', 'senators': 'OTT',
    'red-wings': 'DET', 'maple-leafs': 'TOR', 'oilers': 'EDM', 'panthers': 'FLA', 'lightning': 'TBL',
    'stars': 'DAL', 'avalanche': 'COL', 'devils': 'NJD', 'kraken': 'SEA', 'flames': 'CGY', 'blues': 'STL'
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

INJURY_MAPPING = {
    "lower body": "травма нижней части тела", "undisclosed": "характер травмы не разглашается",
    "hip": "травма бедра", "kneecap": "травма коленной чашечки", "upper body": "травма верхней части тела",
    "ear": "травма уха", "ankle": "травма лодыжки", "foot (leg)": "травма ноги", "heel": "травма пятки",
    "abdomen": "травма брюшной полости", "collarbone": "травма ключицы", "hamstring": "травма задней поверхности бедра",
    "ribs": "травма ребра", "shoulder": "травма плеча", "face": "травма лица", "concussion": "сотрясение мозга",
    "hand": "травма руки", "groin": "травма паха", "personal": "личная причина", "finger": "травма пальца",
    "thumb": "травма большого пальца", "lower leg": "травма голени", "achilles": "травма ахилла",
    "back": "травма спины", "knee": "травма колена", "neck": "травма шеи", "wrist": "травма запястья",
    "illness": "болезнь", "elbow": "травма локтя", "chest": "травма грудной клетки"
}

WAIVER_MAPPING = {"cleared": "прошел драфт отказов", "claimed": "забран с драфта отказов"}

NAV_LINKS_COUNT = 64
CACHE_FILE = "last_data_cache.json"
INJURIES_SNAPSHOT_FILE = "injuries_snapshot.json"

SIGNINGS_API = "https://puckpedia.com/data/api_signings?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A100%2C%22api_url%22%3A%22%2Fdata%2Fapi_signings%22%2C%22url%22%3A%22signings%22%2C%22defaultSort%22%3A%22sign_date%22%2C%22sortBy%22%3A%22sign_date%22%2C%22sortDirection%22%3A%22DESC%22%2C%22sortBySecondary%22%3A%22%22%2C%22sortDirectionSecondary%22%3A%22%22%7D"
TRADES_API = "https://puckpedia.com/data/api_trades?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A40%2C%22api_url%22%3A%22%2Fdata%2Fapi_trades%22%2C%22url%22%3A%22trades%22%2C%22defaultSort%22%3A%22trade_date%22%2C%22sortBy%22%3A%22trade_date%22%2C%22sortDirection%22%3A%22DESC%22%2C%22sortBySecondary%22%3A%22%22%2C%22sortDirectionSecondary%22%3A%22%22%7D"

# =============================================================================
# СНАПШОТ ТРАВМ
# Отдельный файл injuries_snapshot.json — никогда не участвует в миграциях кэша.
# Формат: {"William Carrier": {"team": "CAR", "reason": "травма верхней части тела"}, ...}
# Содержит имена ВСЕХ травмированных на момент последнего сканирования.
# Логика:
#   новый в текущем списке, нет в снапшоте -> публикуем ❌
#   был в снапшоте, пропал из текущего списка -> публикуем ✅
#   снапшот обновляется всегда, независимо от наличия новостей
# =============================================================================

def load_injuries_snapshot():
    """Загружает снапшот из отдельного файла. При отсутствии — пустой словарь."""
    if not os.path.exists(INJURIES_SNAPSHOT_FILE):
        return {}
    try:
        with open(INJURIES_SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Защита: если вдруг файл содержит не словарь — сброс
            if not isinstance(data, dict):
                return {}
            return data
    except Exception:
        return {}

def save_injuries_snapshot(snapshot):
    """Сохраняет снапшот в отдельный файл."""
    with open(INJURIES_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

def commit_file(filepath, message):
    """Коммитит указанный файл в репозиторий."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", filepath], check=True)
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", f"{message} [skip ci]"], check=True)
                subprocess.run(["git", "push"], check=True)
                print(f"  {filepath} сохранён в репозиторий.")
        except Exception as e:
            print(f"  Ошибка сохранения {filepath}: {e}")

# =============================================================================
# КЭШ (подписания, трейды, уэйвер)
# injuries в этом файле больше нет — они живут в injuries_snapshot.json
# =============================================================================

def load_cache():
    default = {
        "signings": {"last_date": "", "last_id": ""},
        "trades": {"last_date": "", "last_id": ""},
        "waivers": {"seen": []}
    }

    if not os.path.exists(CACHE_FILE):
        return default

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return default

    # Миграция: signings
    if isinstance(data.get("signings"), list):
        data["signings"] = {"last_date": "", "last_id": ""}

    # Миграция: trades
    if isinstance(data.get("trades"), list):
        data["trades"] = {"last_date": "", "last_id": ""}

    # Удаляем injuries из основного кэша — они теперь в отдельном файле
    data.pop("injuries", None)

    # Миграция: waivers
    if isinstance(data.get("waivers"), list):
        data["waivers"] = {"seen": []}
    elif isinstance(data.get("waivers"), dict):
        seen = data["waivers"].get("seen", [])
        if seen and any("(" in s or "⬆️" in s or "⬅️" in s or "➡️" in s for s in seen):
            data["waivers"] = {"seen": []}

    for section, default_val in default.items():
        if section not in data:
            data[section] = default_val

    return data

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def extract_player_name(line):
    """Извлекает чистое имя из форматированной строки."""
    clean = line
    for emoji in ["❌", "⬆️", "⬅️", "➡️", "📝", "🔄", "✅"]:
        clean = clean.replace(emoji, "")
    return clean.split("(")[0].strip()

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
    max_len = 4000
    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for part in parts:
        try:
            requests.post(url, data={"chat_id": chat_id, "text": part}, timeout=15)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

def get_team_abbr_by_name(team_name_raw):
    if not team_name_raw:
        return ""
    clean_name = re.sub(r'<[^>]+>', '', str(team_name_raw)).lower().strip()
    for team_key, abbr in TEAM_MAPPING_ABBR.items():
        if team_key in clean_name:
            return f"({abbr})"
    return f"({clean_name[:3].upper()})"

def get_team_abbr_by_slug(slug):
    key = slug.split('/')[-1]
    return TEAM_MAPPING_SLUG.get(key, key.upper())

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

def translate_injury(raw):
    return INJURY_MAPPING.get(raw.lower().strip(), raw)

def format_name(n):
    n = n.replace('\n', ' ').strip()
    if "," in n:
        parts = n.split(",")
        return f"{parts[1].strip()} {parts[0].strip()}"
    return n

def extract_list(data):
    try:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            inner = data.get('data', data)
            if isinstance(inner, list):
                return inner
            if isinstance(inner, dict):
                for key in ('p', 'rows', 'results', 'items', 'data'):
                    if key in inner and isinstance(inner[key], list):
                        return inner[key]
    except Exception as e:
        print(f"Ошибка извлечения списка: {e}")
    return []

async def fetch_api(page, url, label):
    for attempt in range(5):
        try:
            api_response = await page.evaluate('''async (fetchUrl) => {
                const resp = await fetch(fetchUrl, {
                    headers: {
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });
                const text = await resp.text();
                return {status: resp.status, body: text};
            }''', url)
            status = api_response['status']
            print(f"  {label} попытка {attempt + 1}: статус {status}")
            if status == 200:
                data = json.loads(api_response['body'])
                result = extract_list(data)
                print(f"  Получено записей: {len(result)}")
                return result
            elif status == 403:
                print(f"  403 Cloudflare — ждём 10 сек и повторяем...")
                await asyncio.sleep(10)
            else:
                print(f"  Неожиданный статус, ждём 5 сек...")
                await asyncio.sleep(5)
        except Exception as e:
            print(f"  Ошибка: {e}, ждём 5 сек...")
            await asyncio.sleep(5)
    return []

async def get_team_from_profile(page, player_url):
    await page.goto(f"https://puckpedia.com{player_url}", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(1.5)
    all_team_links = await page.eval_on_selector_all(
        "a[href*='/team/']",
        "els => els.map(e => e.getAttribute('href'))"
    )
    if len(all_team_links) > NAV_LINKS_COUNT:
        return get_team_abbr_by_slug(all_team_links[NAV_LINKS_COUNT])
    return "UNK"

# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# =============================================================================

async def main():
    raw_signings = []
    raw_trades = []
    current_waivers = []

    # Травмы: два уровня
    # current_injuries_top  — топ-3 с командой и причиной для публикации новых
    # current_injury_names_all — все имена для отслеживания выздоровлений
    current_injuries_top = []    # список (name, team, reason)
    current_injury_names_all = set()  # множество всех имён на странице

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # --- ПОДПИСАНИЯ ---
        print("Открываем страницу подписаний...")
        await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(10)
        raw_signings = await fetch_api(page, SIGNINGS_API, "Подписания")

        # --- ТРЕЙДЫ ---
        print("Открываем страницу трейдов...")
        await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(10)
        raw_trades = await fetch_api(page, TRADES_API, "Трейды")

        # --- ТРАВМЫ ---
        print("Открываем страницу травм...")
        await page.goto("https://puckpedia.com/injuries", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)

        # Все строки где ссылка ведёт именно на профиль игрока (/player/)
        # Это исключает строки-разделители команд у которых ссылка /team/
        all_player_rows = await page.query_selector_all("tr:has(a.pp_link[href*='/player/'])")
        print(f"  Строк с игроками на странице: {len(all_player_rows)}")

        # Проход 1: собираем ВСЕ имена — без заходов в профили
        for row in all_player_rows:
            cells = await row.query_selector_all("td")
            if not cells:
                continue
            # Берём только ссылку на профиль игрока
            name_link = await cells[0].query_selector("a.pp_link[href*='/player/']")
            if not name_link:
                continue
            raw_name = format_name((await name_link.inner_text()).strip())
            if raw_name and len(raw_name) > 2:
                current_injury_names_all.add(raw_name)

        print(f"  Всего травмированных имён: {len(current_injury_names_all)}")

        # Проход 2: топ-3 — заходим в профили для определения команды
        raw_injury_entries = []
        for row in all_player_rows[:3]:
            cells = await row.query_selector_all("td")
            if not cells:
                continue
            name_link = await cells[0].query_selector("a.pp_link[href*='/player/']")
            if not name_link:
                continue
            player_url = await name_link.get_attribute("href")
            name = format_name((await name_link.inner_text()).strip())
            reason = translate_injury((await cells[3].inner_text()).strip()) if len(cells) > 3 else "характер травмы не разглашается"
            raw_injury_entries.append((name, reason, player_url))

        for name, reason, player_url in raw_injury_entries:
            team_abbr = await get_team_from_profile(page, player_url) if player_url else "UNK"
            current_injuries_top.append((name, team_abbr, reason))
            print(f"  Топ-3 травма: ❌ {name} ({team_abbr}), {reason}")

        # --- УЭЙВЕР ---
        print("Открываем страницу уэйвера...")
        await page.goto("https://puckpedia.com/waiver-wire", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        rows = await page.query_selector_all("tr")
        count = 0
        for row in rows:
            cells = await row.query_selector_all("td")
            if len(cells) >= 3:
                name = format_name((await cells[0].inner_text()).strip())
                team_full = (await cells[1].inner_text()).strip().lower().replace(" ", "-")
                team_abbr = get_team_abbr_by_slug(team_full)
                res = (await cells[2].inner_text()).strip().lower()
                waiver_text = WAIVER_MAPPING.get(res, res)
                if res == "claimed":
                    emoji = "⬆️"
                elif res == "cleared":
                    emoji = "⬅️"
                else:
                    emoji = "➡️"
                line = f"{emoji} {name} ({team_abbr}) {waiver_text}"
                current_waivers.append(line)
                print(f"  Уэйвер: {line}")
                count += 1
                if count >= 3:
                    break

        await browser.close()

    # --- ПРОВЕРКА ЗАГРУЗКИ ---
    if not raw_signings:
        print("Подписания не загрузились. Операция прервана.")
        return
    if not raw_trades:
        print("Трейды не загрузились. Операция прервана.")
        return

    # --- ЗАГРУЖАЕМ СНАПШОТ ТРАВМ ---
    prev_snapshot = load_injuries_snapshot()
    prev_names = set(prev_snapshot.keys())
    is_first_run = len(prev_snapshot) == 0

    print(f"Снапшот травм: было {len(prev_names)}, сейчас {len(current_injury_names_all)}")

    # --- ЗАГРУЖАЕМ ОСНОВНОЙ КЭШ ---
    cache = load_cache()
    all_new = []

    # --- ПОДПИСАНИЯ ---
    last_sign_date = cache["signings"].get("last_date", "")
    last_sign_id = cache["signings"].get("last_id", "")

    new_signings_raw = []
    for item in raw_signings:
        item_date = str(item.get("sign_date", "") or "")
        item_id = str(item.get("cid", "") or item.get("id", "") or "")
        if item_date > last_sign_date:
            new_signings_raw.append(item)
        elif item_date == last_sign_date and item_id and item_id != last_sign_id:
            new_signings_raw.append(item)
        else:
            break

    print(f"Новых подписаний: {len(new_signings_raw)}")

    for item in new_signings_raw:
        p_fn = str(item.get('p_fn', '')).strip()
        p_ln = str(item.get('p_ln', '')).strip()
        name = f"{p_fn} {p_ln}".strip()
        if not name:
            continue
        lvl = str(item.get('lvl', '')).upper()
        cap_hit = item.get('cap_hit', 0) or 0
        try:
            cap_val = float(str(cap_hit).replace(',', '')) / 10
        except:
            cap_val = 0
        years_raw = str(item.get('len', 1) or 1)
        try:
            years = int(re.sub(r'[^0-9]', '', years_raw) or 1)
        except:
            years = 1
        sign_city = str(item.get('sign_city', '')).strip()
        sign_team_name = str(item.get('sign_team_name', '')).strip()
        team_name = f"{sign_city} {sign_team_name}".strip()
        raw_type = str(item.get('type_name', '')).lower()
        if "extension" in raw_type:
            ctype = "продлил контракт"
        else:
            ctype = "подписал контракт новичка" if "ELC" in lvl else "подписал контракт"
        line = f"📝 {name} {ctype} {format_years(years)} с кэпхитом {format_cap_hit(cap_val)} {get_team_abbr_by_name(team_name)}"
        all_new.append(line)

    if raw_signings:
        cache["signings"]["last_date"] = str(raw_signings[0].get("sign_date", "") or "")
        cache["signings"]["last_id"] = str(raw_signings[0].get("cid", "") or raw_signings[0].get("id", "") or "")

    # --- ТРЕЙДЫ ---
    last_trade_date = cache["trades"].get("last_date", "")
    last_trade_id = cache["trades"].get("last_id", "")

    new_trades_raw = []
    for item in raw_trades:
        item_date = str(item.get("trade_date", "") or "")
        item_id = str(item.get("trade_id", "") or "")
        if item_date > last_trade_date:
            new_trades_raw.append(item)
        elif item_date == last_trade_date and item_id and item_id != last_trade_id:
            new_trades_raw.append(item)
        else:
            break

    print(f"Новых трейдов: {len(new_trades_raw)}")

    seen_trades = set()
    for item in new_trades_raw:
        text = str(item.get('details_nolinks', '') or item.get('details', '') or '').strip()
        if not text or len(text) < 20:
            continue
        translated = translate_trade(text)
        if translated not in seen_trades and "The ID of this channel" not in translated:
            seen_trades.add(translated)
            all_new.append(f"🔄 {translated}")

    if raw_trades:
        cache["trades"]["last_date"] = str(raw_trades[0].get("trade_date", "") or "")
        cache["trades"]["last_id"] = str(raw_trades[0].get("trade_id", "") or "")

    # --- ТРАВМЫ ---
    if is_first_run:
        # Первый запуск — снапшот пуст, просто сохраняем текущий список
        # Ничего не публикуем, чтобы не засорить канал всеми ~150 травмами сразу
        print("Первый запуск: снапшот травм создаётся, публикаций нет.")
    else:
        # Новые травмы: есть в текущем списке, нет в снапшоте, есть в топ-3
        for name, team_abbr, reason in current_injuries_top:
            if name not in prev_names:
                line = f"❌ {name} ({team_abbr}), {reason}"
                all_new.append(line)
                print(f"  Новая травма: {line}")

        # Выздоровления: были в снапшоте, пропали из текущего полного списка
        recovered = prev_names - current_injury_names_all
        for name in sorted(recovered):
            line = f"✅ {name} активирован из списка травмированных"
            all_new.append(line)
            print(f"  Выздоровление: {line}")

        print(f"Новых травм в топ-3: {sum(1 for n,_,_ in current_injuries_top if n not in prev_names)}, выздоровлений: {len(recovered)}")

    # Обновляем снапшот — сохраняем все текущие имена
    # Для топ-3 сохраняем полные данные (команда, причина), для остальных — просто имя
    new_snapshot = {}
    for name in current_injury_names_all:
        # Если есть полные данные из топ-3 — используем их
        top3_data = {n: (t, r) for n, t, r in current_injuries_top}
        if name in top3_data:
            team, reason = top3_data[name]
            new_snapshot[name] = {"team": team, "reason": reason}
        elif name in prev_snapshot:
            # Сохраняем старые данные если игрок уже был в снапшоте
            new_snapshot[name] = prev_snapshot[name]
        else:
            # Новый игрок не из топ-3 — сохраняем без деталей
            new_snapshot[name] = {"team": "UNK", "reason": ""}

    # --- УЭЙВЕР ---
    seen_waiver_names = set(cache["waivers"].get("seen", []))
    new_waivers = []
    new_waiver_names = []
    for line in current_waivers:
        player_name = extract_player_name(line)
        if player_name and player_name not in seen_waiver_names:
            new_waivers.append(line)
            new_waiver_names.append(player_name)

    print(f"Новых уэйверов: {len(new_waivers)}")
    all_new.extend(new_waivers)
    cache["waivers"]["seen"] = list(seen_waiver_names) + new_waiver_names

    # --- СОХРАНЯЕМ СНАПШОТ ТРАВМ (всегда) ---
    save_injuries_snapshot(new_snapshot)
    commit_file(INJURIES_SNAPSHOT_FILE, "Обновление снапшота травм")

    # --- СОХРАНЯЕМ ОСНОВНОЙ КЭШ (всегда) ---
    save_cache(cache)
    commit_file(CACHE_FILE, "Обновление кэша")

    if not all_new:
        print("Новых событий нет. Скрипт завершен без отправки.")
        return

    message = "\n\n".join(all_new)
    send_to_telegram(message)
    print(f"Отправлено {len(all_new)} новых записей в Telegram.")

if __name__ == "__main__":
    asyncio.run(main())
