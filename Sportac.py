import asyncio
import os
import re
import subprocess
import requests
import json
from playwright.async_api import async_playwright

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
    'Calgary Flames': {'main': 'Калгари обменяли', 'from': 'из Калкари'},
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
    "abdomen": "травма брюшной полости", "collarbone": "травма ключицы",
    "hamstring": "травма задней поверхности бедра", "ribs": "травма ребра", "shoulder": "травма плеча",
    "face": "травма лица", "concussion": "сотрясение мозга", "hand": "травма руки", "groin": "травма паха",
    "personal": "личная причина", "finger": "травма пальца", "thumb": "травма большого пальца",
    "lower leg": "травма голени", "achilles": "травма ахилла", "arm": "травма руки",
    "back": "травма спины", "knee": "травма колена", "neck": "травма шеи", "wrist": "травма запястья",
    "illness": "болезнь", "elbow": "травма локтя", "chest": "травма грудной клетки"
}

WAIVER_MAPPING = {"cleared": "прошел драфт отказов", "claimed": "забран с драфта отказов"}

AHL_TEAM_MAPPING = {
    'chicago': 'CAR', 'colorado': 'COL', 'henderson': 'VGK', 'laval': 'MTL', 'springfield': 'STL',
    'toronto': 'TOR', 'belleville': 'OTT', 'utica': 'VAN', 'san jose': 'SJS', 'san diego': 'ANA',
    'bakersfield': 'EDM', 'abbotsford': 'VAN', 'iowa': 'MIN', 'milwaukee': 'NAS', 'cleveland': 'CBJ',
    'grand rapids': 'DET', 'charlotte': 'FLA', 'hershey': 'WSH', 'lehigh valley': 'PHI', 'hartford': 'NYR',
    'bridgeport': 'NYI', 'binghamton': 'NJD', 'rockford': 'CHI', 'texas': 'DAL', 'coachella': 'SEA',
    'providence': 'BOS', 'rochester': 'BUF', 'syracuse': 'TBL', 'manitoba': 'WPG', 'ontario': 'LAK',
    'stockton': 'CGY', 'calgary wranglers': 'CGY', 'wranglers': 'CGY', 'tucson': 'UTAH', 'wilkes': 'PIT',
    'lehigh': 'PHI', 'new jersey': 'NJD', 'pittsburgh': 'PIT', 'seattle': 'SEA',
}

GAMES_WORD_MAP = {
    'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
    'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'
}

NAV_LINKS_COUNT = 64
CACHE_FILE = "last_data_cache.json"
TRANSACTIONS_CACHE_FILE = "transactions_cache.json"
INJURIES_SNAPSHOT_FILE = "injuries_snapshot.json"
INJURIES_MIN_COUNT = 50

SIGNINGS_API = "https://puckpedia.com/data/api_signings?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A100%2C%22api_url%22%3A%22%2Fdata%2Fapi_signings%22%2C%22url%22%3A%22signings%22%2C%22defaultSort%22%3A%22sign_date%22%2C%22sortBy%22%3A%22sign_date%22%2C%22sortDirection%22%3A%22DESC%22%2C%22sortBySecondary%22%3A%22%22%2C%22sortDirectionSecondary%22%3A%22%22%7D"
TRADES_API = "https://puckpedia.com/data/api_trades?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A40%2C%22api_url%22%3A%22%2Fdata%2Fapi_trades%22%2C%22url%22%3A%22trades%22%2C%22defaultSort%22%3A%22trade_date%22%2C%22sortBy%22%3A%22trade_date%22%2C%22sortDirection%22%3A%22DESC%22%2C%22sortBySecondary%22%3A%22%22%2C%22sortDirectionSecondary%22%3A%22%22%7D"
TRANSACTIONS_API = "https://puckpedia.com/data/api_transactions?q=%7B%22curPage%22%3A1%2C%22pageSize%22%3A40%2C%22api_url%22%3A%22%2Fdata%2Fapi_transactions%22%2C%22url%22%3A%22transactions%22%2C%22transaction_type%22%3A%22roster%22%2C%22defaultSort%22%3A%22sort_date%22%2C%22sortBy%22%3A%22sort_date%22%2C%22sortDirection%22%3A%22DESC%22%2C%22sortBySecondary%22%3A%22%22%2C%22sortDirectionSecondary%22%3A%22%22%7D"


def normalize_games(text):
    def replace_word(m):
        word = m.group(1).lower()
        num = GAMES_WORD_MAP.get(word, word)
        count = int(num) if num.isdigit() else 1
        if count == 1:
            return f"{num} игру"
        elif 2 <= count <= 4:
            return f"{num} игры"
        else:
            return f"{num} игр"
    text = re.sub(r'\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+games?\b', replace_word, text, flags=re.I)
    text = re.sub(r'\b(\d+)\s+games?\b', lambda m: (
        f"{m.group(1)} игру" if m.group(1) == '1'
        else f"{m.group(1)} игры" if int(m.group(1)) in (2, 3, 4)
        else f"{m.group(1)} игр"
    ), text)
    return text


def get_ahl_nhl_abbr(ahl_city_raw):
    key = ahl_city_raw.lower().strip()
    if key in AHL_TEAM_MAPPING:
        return AHL_TEAM_MAPPING[key]
    for k, v in AHL_TEAM_MAPPING.items():
        if k in key or key in k:
            return v
    return ""


def clean_league_prefix(text):
    text = re.sub(
        r'\b(Swedish|Finnish|Russian|Swiss|German|Czech|Slovak|Austrian|Danish|Norwegian|KHL|SHL|Liiga|DEL|NL|ICEHL)\s+club\s+',
        '', text, flags=re.I)
    text = re.sub(
        r'\b(Swedish|Finnish|Russian|Swiss|German|Czech|Slovak|Austrian|Danish|Norwegian)\s+',
        '', text, flags=re.I)
    return text.strip()


TRANSACTION_PATTERNS = [
    (re.compile(r'(\w+)\s+was (?:reassigned|sent) to AHL (\w[\w\s\-]+?)(?:\s+on\s+\w+day|\s+per\b|\s*,|\s*\.)', re.I),
     lambda m: (m.group(1), 'ahl_to', m.group(2).strip())),
    (re.compile(r'(\w+)\s+was (?:recalled|promoted|called up|brought up|summoned|elevated)\s+from AHL (\w[\w\s\-]+?)(?:\s+on\s+\w+day|\s+per\b|\s*,|\s*\.)', re.I),
     lambda m: (m.group(1), 'ahl_from', m.group(2).strip())),
    (re.compile(r'(\w+)\s+was elevated from the minors', re.I),
     lambda m: (m.group(1), 'minors_from', '')),
    (re.compile(r'(\w+)\s+was summoned by (?:the\s+)?(.+?) from (?:OHL|WHL|QMJHL|AHL|ECHL)\s+(\w[\w\s\-]+?)(?:\s+on\s+\w+day|\s*\.|\s*,)', re.I),
     lambda m: (m.group(1), 'summoned_by', m.group(3).strip())),
    (re.compile(r'(\w+)\s+(?:\([^)]+\)\s+)?(?:has been |was )?placed on (?:the\s+)?injured reserve|IR\b', re.I),
     lambda m: (m.group(1), 'placed_ir', '')),
    (re.compile(r'(\w+)\s+(?:\([^)]+\)\s+)?(?:has been |was )?activated from (?:the\s+)?(?:long-term\s+)?(?:injured reserve|IR\b)', re.I),
     lambda m: (m.group(1), 'activated_ir', '')),
    (re.compile(r'(\w+)\s+(?:\([^)]+\)\s+)?will be activated from (?:long-term\s+)?(?:injured reserve|LTIR)\b', re.I),
     lambda m: (m.group(1), 'will_activated_ltir', '')),
    (re.compile(r'(\w+)\s+(?:\([^)]+\)\s+)?(?:has been |was )?placed on (?:the\s+)?LTIR\b', re.I),
     lambda m: (m.group(1), 'placed_ltir', '')),
    (re.compile(r'(\w+)\s+(?:\([^)]+\)\s+)?(?:has been |was )?activated from (?:the\s+)?LTIR\b', re.I),
     lambda m: (m.group(1), 'activated_ltir', '')),
    (re.compile(r'(\w+)\s+was suspended for ([\w\s]+?games?)\b', re.I),
     lambda m: (m.group(1), 'suspended', normalize_games(m.group(2).strip()))),
    (re.compile(r'(\w+)\s+is eligible to play', re.I),
     lambda m: (m.group(1), 'eligible', '')),
    (re.compile(r'(\w+)\s+(?:has been |was )?claimed (?:off waivers\s+)?by (?:the\s+)?(.+?)(?:\s+on\s+\w+day|\s*\.|\s*,)', re.I),
     lambda m: (m.group(1), 'claimed', m.group(2).strip())),
    (re.compile(r'(\w+)\s+(?:has\s+)?cleared waivers', re.I),
     lambda m: (m.group(1), 'cleared_waivers', '')),
    (re.compile(r'(\w+)\s+(?:has been |was )?released\b', re.I),
     lambda m: (m.group(1), 'released', '')),
    (re.compile(r'(\w+)\s+(?:announced|is)\s+.{0,40}(?:retiring|retirement|ending his playing career)', re.I),
     lambda m: (m.group(1), 'retiring', '')),
    (re.compile(r'(\w+)\s+(?:has been |was )?loaned to (.+?)(?:\s+on\s+\w+day|\s*\.|\s*,)', re.I),
     lambda m: (m.group(1), 'loaned', clean_league_prefix(m.group(2).strip()))),
    (re.compile(r'(\w+)\s+(?:has been |was )?signed (?:to\s+)?(?:a\s+)?PTO\b', re.I),
     lambda m: (m.group(1), 'pto', '')),
    (re.compile(r'(\w+)\s+(?:agreed to terms on (?:a\s+)?contract with|signed (?:a\s+)?contract with)\s+(.+?)(?:\s+on\s+\w+day|\s*\.|\s*,)', re.I),
     lambda m: (m.group(1), 'foreign_contract', clean_league_prefix(m.group(2).strip()))),
    (re.compile(r'(\w+)\s+committed to (?:the\s+)?(.+?)(?:\s+ahead of|\s+for the|\s+on\s+\w+day|\s*\.)', re.I),
     lambda m: (m.group(1), 'committed', m.group(2).strip())),
    (re.compile(r'(\w+)\s+(?:has been |was )?assigned to (?:the\s+)?AHL\b', re.I),
     lambda m: (m.group(1), 'assigned_ahl', '')),
]


def build_transaction_line(parsed):
    name, action, arg = parsed
    if action == 'ahl_to':
        ahl_abbr = get_ahl_nhl_abbr(arg)
        abbr_str = f" ({ahl_abbr})" if ahl_abbr else ""
        return f"{name} переведён в АХЛ ({arg}){abbr_str}"
    elif action == 'ahl_from':
        ahl_abbr = get_ahl_nhl_abbr(arg)
        abbr_str = f" ({ahl_abbr})" if ahl_abbr else ""
        return f"{name} вызван из АХЛ ({arg}){abbr_str}"
    elif action == 'minors_from':
        return f"{name} вызван из минорных лиг"
    elif action == 'summoned_by':
        return f"{name} вызван из {arg}"
    elif action == 'placed_ir':
        return f"{name} переведён в список травмированных"
    elif action == 'activated_ir':
        return f"{name} активирован из списка травмированных"
    elif action == 'will_activated_ltir':
        return f"{name} будет активирован из долгосрочного списка травмированных"
    elif action == 'placed_ltir':
        return f"{name} переведён в долгосрочный список травмированных (LTIR)"
    elif action == 'activated_ltir':
        return f"{name} активирован из долгосрочного списка травмированных (LTIR)"
    elif action == 'suspended':
        return f"{name} дисквалифицирован на {arg}"
    elif action == 'eligible':
        return f"{name} вернулся после дисквалификации"
    elif action == 'claimed':
        return f"{name} подобран с драфта отказов командой {arg}"
    elif action == 'cleared_waivers':
        return f"{name} прошёл драфт отказов"
    elif action == 'released':
        return f"{name} освобождён"
    elif action == 'retiring':
        return f"{name} завершает карьеру"
    elif action == 'loaned':
        return f"{name} отдан в аренду ({arg})"
    elif action == 'pto':
        return f"{name} подписан на пробный контракт (PTO)"
    elif action == 'foreign_contract':
        return f"{name} подписал контракт с {arg}"
    elif action == 'committed':
        return f"{name} переходит в студенческую команду {arg}"
    elif action == 'assigned_ahl':
        return f"{name} направлен в АХЛ"
    return ""


def translate_transaction(raw_text):
    text = re.sub(r'<[^>]+>', '', raw_text).strip()
    for pattern, extractor in TRANSACTION_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                parsed = extractor(m)
                result = build_transaction_line(parsed)
                if result:
                    return result
            except Exception:
                continue
    return text


def load_transactions_cache():
    default = {"last_date": "", "last_id": "", "recent": []}
    if not os.path.exists(TRANSACTIONS_CACHE_FILE):
        return default
    try:
        with open(TRANSACTIONS_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default
        for k, v in default.items():
            if k not in data:
                data[k] = v
        return data
    except Exception:
        return default


def save_transactions_cache(cache):
    with open(TRANSACTIONS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def load_injuries_snapshot():
    if not os.path.exists(INJURIES_SNAPSHOT_FILE):
        return {}
    try:
        with open(INJURIES_SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_injuries_snapshot(snapshot):
    with open(INJURIES_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def commit_file(filepath, message):
    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", filepath], check=True)
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", f"{message} [skip ci]"], check=True)
                subprocess.run(["git", "push"], check=True)
                print(f"  {filepath} сохранён.")
        except Exception as e:
            print(f"  Ошибка сохранения {filepath}: {e}")


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
    for key in ("signings", "trades"):
        if not isinstance(data.get(key), dict):
            data[key] = {"last_date": "", "last_id": ""}
    data.pop("injuries", None)
    data.pop("transactions", None)
    if not isinstance(data.get("waivers"), dict):
        data["waivers"] = {"seen": []}
    elif "seen" not in data["waivers"]:
        data["waivers"]["seen"] = []
    for k, v in default.items():
        if k not in data:
            data[k] = v
    return data


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def commit_cache():
    if os.environ.get("GITHUB_ACTIONS") == "true":
        try:
            subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", CACHE_FILE], check=True)
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", "Обновление кэша [skip ci]"], check=True)
                subprocess.run(["git", "push"], check=True)
                print("Кэш сохранён.")
        except Exception as e:
            print(f"Ошибка кэша: {e}")


def extract_player_name(line):
    clean = line
    for emoji in ["❌", "✅", "⬆️", "⬅️", "➡️", "📝", "🔄", "🏒"]:
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
    except Exception:
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
    except Exception:
        return f"{val_raw}"


def translate_trade(text):
    if "forfeit" in text.lower():
        return text
    for pattern in [
        r"The (.+?) acquire (.+?) from the (.+?) for (.+)",
        r"The (.+?) acquire (.+?) from (.+?) for (.+)"
    ]:
        match = re.search(pattern, text)
        if match:
            team1, p1, team2, p2 = match.groups()
            r1 = get_rus_team_data(team1)
            r2 = get_rus_team_data(team2)
            
            # Очищаем списки обмениваемых активов от английских артиклей "a " и "an " перед пиками/игроками
            p1 = re.sub(r'\b[aA](n)?\s+', '', p1)
            p2 = re.sub(r'\b[aA](n)?\s+', '', p2)
            
            p1 = p1.replace(".", "").replace(" and ", " и ")
            p2 = p2.replace(".", "").replace(" and ", " и ")
            return f"{r1['main']} {p2} на {p1} {r2['from']}"
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
                print(f"  403 — ждём 10 сек...")
                await asyncio.sleep(10)
            else:
                print(f"  Статус {status} — ждём 5 сек...")
                await asyncio.sleep(5)
        except Exception as e:
            print(f"  Ошибка: {e} — ждём 5 сек...")
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


async def main():
    raw_signings = []
    raw_trades = []
    raw_transactions = []
    current_waivers = []
    current_injury_names_all = set()
    current_injury_urls = {}
    current_injuries_top = []
    injuries_loaded_ok = False
    prev_snapshot = {}
    prev_names = set()
    recovered_lines = []

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

        # --- ТРАНЗАКЦИИ ---
        print("Открываем страницу транзакций...")
        await page.goto("https://puckpedia.com/transactions?transaction_type=roster", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(10)
        raw_transactions = await fetch_api(page, TRANSACTIONS_API, "Транзакции")

        # --- ТРАВМЫ ---
        print("Открываем страницу травм...")
        await page.goto("https://puckpedia.com/injuries", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)

        all_player_rows = await page.query_selector_all("tr:has(a.pp_link[href*='/player/'])")
        print(f"  Строк с игроками: {len(all_player_rows)}")

        for row in all_player_rows:
            cells = await row.query_selector_all("td")
            if not cells:
                continue
            name_link = await cells[0].query_selector("a.pp_link[href*='/player/']")
            if not name_link:
                continue
            raw_name = format_name((await name_link.inner_text()).strip())
            player_url = await name_link.get_attribute("href")
            if raw_name and len(raw_name) > 2:
                current_injury_names_all.add(raw_name)
                if player_url:
                    current_injury_urls[raw_name] = player_url

        print(f"  Всего травмированных: {len(current_injury_names_all)}")

        if len(current_injury_names_all) >= INJURIES_MIN_COUNT:
            injuries_loaded_ok = True
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
                current_injuries_top.append((name, team_abbr, reason, player_url))
                print(f"  Топ-3: {name} ({team_abbr}), {reason}")

            prev_snapshot = load_injuries_snapshot()
            prev_names = set(prev_snapshot.keys())
            recovered = prev_names - current_injury_names_all

            if recovered and len(prev_names) > 0:
                print(f"  Выздоровевших: {len(recovered)}")
                for name in sorted(recovered):
                    player_url = prev_snapshot[name].get("url", "")
                    if player_url:
                        team_abbr = await get_team_from_profile(page, player_url)
                        line = (f"✅ {name} ({team_abbr}) активирован из списка травмированных"
                                if team_abbr and team_abbr != "UNK"
                                else f"✅ {name} активирован из списка травмированных")
                    else:
                        line = f"✅ {name} активирован из списка травмированных"
                    recovered_lines.append(line)
                    print(f"  Выздоровление: {line}")
        else:
            print(f"  ЗАЩИТА: список травм мал ({len(current_injury_names_all)} < {INJURIES_MIN_COUNT}), блок пропускается.")
            prev_snapshot = load_injuries_snapshot()
            prev_names = set(prev_snapshot.keys())

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
                emoji = "⬆️" if res == "claimed" else ("⬅️" if res == "cleared" else "➡️")
                line = f"{emoji} {name} ({team_abbr}) {waiver_text}"
                current_waivers.append(line)
                print(f"  Уэйвер: {line}")
                count += 1
                if count >= 3:
                    break

        await browser.close()

    if not raw_signings:
        print("Подписания не загрузились. Операция прервана.")
        return
    if not raw_trades:
        print("Трейды не загрузились. Операция прервана.")
        return

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
        except Exception:
            cap_val = 0
        years_raw = str(item.get('len', 1) or 1)
        try:
            years = int(re.sub(r'[^0-9]', '', years_raw) or 1)
        except Exception:
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

    # --- ТРАНЗАКЦИИ ---
    tx_cache = load_transactions_cache()
    last_tx_date = tx_cache.get("last_date", "")
    last_tx_id = tx_cache.get("last_id", "")

    all_tx_lines_for_recent = []
    for item in raw_transactions[:5]:
        raw_text = str(item.get('details', '') or item.get('details_nolinks', '') or '').strip()
        if raw_text and len(raw_text) >= 10:
            all_tx_lines_for_recent.append(translate_transaction(raw_text))
    tx_cache["recent"] = all_tx_lines_for_recent
    print(f"  recent обновлён: {all_tx_lines_for_recent}")

    new_transactions_raw = []
    for item in raw_transactions:
        item_date = str(item.get("sort_date", "") or item.get("transaction_date", "") or "")
        item_id = str(item.get("transaction_id", "") or item.get("id", "") or "")
        if item_date > last_tx_date:
            new_transactions_raw.append(item)
        elif item_date == last_tx_date and item_id and item_id != last_tx_id:
            new_transactions_raw.append(item)
        else:
            break

    print(f"Новых транзакций: {len(new_transactions_raw)}")
    seen_tx = set()
    for item in new_transactions_raw:
        raw_text = str(item.get('details', '') or item.get('details_nolinks', '') or '').strip()
        if not raw_text or len(raw_text) < 10:
            continue
        translated = translate_transaction(raw_text)
        if translated not in seen_tx:
            seen_tx.add(translated)
            all_new.append(f"🏒 {translated}")

    if raw_transactions:
        first = raw_transactions[0]
        tx_cache["last_date"] = str(first.get("sort_date", "") or first.get("transaction_date", "") or "")
        tx_cache["last_id"] = str(first.get("transaction_id", "") or first.get("id", "") or "")

    save_transactions_cache(tx_cache)
    commit_file(TRANSACTIONS_CACHE_FILE, "Обновление кэша транзакций")

    # --- ТРАВМЫ ---
    if injuries_loaded_ok:
        is_first_run = len(prev_snapshot) == 0
        if is_first_run:
            print("Первый запуск снапшота травм: публикаций нет, снапшот создаётся.")
        else:
            for name, team_abbr, reason, _ in current_injuries_top:
                if name not in prev_names:
                    all_new.append(f"❌ {name} ({team_abbr}), {reason}")
                    print(f"  Новая травма: {name}")
            all_new.extend(recovered_lines)

        new_snapshot = {}
        top3_dict = {n: (t, r, u) for n, t, r, u in current_injuries_top}
        for name in current_injury_names_all:
            if name in top3_dict:
                team, reason, url = top3_dict[name]
                new_snapshot[name] = {"team": team, "reason": reason, "url": url or ""}
            elif name in prev_snapshot:
                new_snapshot[name] = prev_snapshot[name]
            else:
                new_snapshot[name] = {"team": "UNK", "reason": "", "url": current_injury_urls.get(name, "")}

        save_injuries_snapshot(new_snapshot)
        commit_file(INJURIES_SNAPSHOT_FILE, "Обновление снапшота травм")
        print(f"Снапшот травм обновлён: {len(new_snapshot)} игроков.")
    else:
        print("Снапшот травм не обновляется.")

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

    # --- СОХРАНЯЕМ КЭШ ---
    save_cache(cache)
    commit_cache()

    if not all_new:
        print("Новых событий нет. Скрипт завершен без отправки.")
        return

    message = "\n\n".join(all_new)
    send_to_telegram(message)
    print(f"Отправлено {len(all_new)} новых записей в Telegram.")


if __name__ == "__main__":
    asyncio.run(main())
