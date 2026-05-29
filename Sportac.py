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
    if not token or not chat_id: return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    max_len = 3500
    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for part in parts:
        try:
            requests.post(url, data={"chat_id": chat_id, "text": part}, timeout=15)
        except Exception as e:
            print(f"Ошибка отправки: {e}")

def get_team_abbr(team_name_raw):
    if not team_name_raw: return ""
    clean_name = re.sub(r'<[^>]+>', '', str(team_name_raw)).lower().strip()
    for team_key, abbr in TEAM_MAPPING.items():
        if team_key in clean_name: return f"({abbr})"
    return f"({clean_name[:3].upper()})"

def format_years(years_raw):
    try:
        years = int(re.sub(r'[^0-9]', '', str(years_raw)))
    except:
        return "на срок"
    if years == 1: return "на 1 год"
    elif 2 <= years <= 4: return f"на {years} года"
    else: return f"на {years} лет"

def format_cap_hit(val_raw):
    try:
        # Переводим в float, а затем в int, чтобы убрать копейки и избежать склеивания с нулем
        clean_val = int(float(val_raw))
        return f"${clean_val:,}"
    except:
        return f"${val_raw}"

def translate_trade(text):
    if "forfeit" in text.lower(): return text
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
        
        # Десктопное разрешение для рендеринга классов lg:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        # --- СБОР ПОДПИСАНИЙ ---
        print("Загрузка страницы подписаний...")
        try:
            # domcontentloaded - работает быстро и не ждет бесконечной загрузки рекламы
            await page.goto("https://puckpedia.com/signings", wait_until="domcontentloaded", timeout=30000)
            
            # Небольшой скролл для активации прогрузки (lazy-load)
            await page.evaluate("window.scrollBy(0, 800)")
            
            # Просто ждем, пока на странице появятся ссылки на игроков
            await page.wait_for_selector('a[href*="/player"]', timeout=15000)
            
            # Даем скриптам сайта еще пару секунд, чтобы они точно расставили все классы
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Предупреждение по подписаниям: {e}")

        # Сбор данных с помощью JavaScript
        extracted_signings = await page.evaluate("""() => {
            // Ищем контейнеры с нужными классами
            const blocks = Array.from(document.querySelectorAll('div')).filter(el => 
                el.className && 
                typeof el.className === 'string' &&
                el.className.includes('flex') && 
                el.className.includes('items-start') && 
                el.className.includes('flex-col') && 
                el.className.includes('lg:flex-row')
            );
            
            let results = [];
            let seenNames = new Set();
            
            for (let container of blocks) {
                // --- ИМЯ ИГРОКА ---
                const nameLink = container.querySelector('a[href*="/player"]');
                let nameText = '';
                
                if (nameLink) {
                    nameText = nameLink.innerText.trim();
                } else {
                    const boldText = container.querySelector('.font-bold, font-semibold, h2, h3, strong');
                    if (boldText) nameText = boldText.innerText.trim();
                }
                
                if (!nameText || seenNames.has(nameText)) continue;
                seenNames.add(nameText);
                const parts = nameText.split(' ');
                
                // --- КОМАНДА ---
                const teamLink = container.querySelector('a[href*="/team"]');
                let team_name = '';
                if (teamLink) {
                    team_name = teamLink.innerText.trim();
                } else {
                    const teamImg = container.querySelector('img[alt*="logo"]');
                    if (teamImg) team_name = teamImg.getAttribute('alt').replace(/logo/i, '').trim();
                }

                // --- ДЕТАЛИ КОНТРАКТА ---
                let len = '1';
                let cval = '0';
                let type_name = '';
                let lvl = '';
                
                const rawText = container.innerText || '';
                // Разбиваем текст по переносам строк, чтобы читать пары "Ключ" -> "Значение"
                const lines = rawText.split(String.fromCharCode(10)).map(l => l.trim()).filter(l => l);
                
                for (let i = 0; i < lines.length; i++) {
                    const lowerLine = lines[i].toLowerCase();
                    if ((lowerLine === 'length' || lowerLine === 'term') && lines[i+1]) {
                        len = lines[i+1];
                    } else if ((lowerLine === 'cap hit' || lowerLine === 'aav') && lines[i+1]) {
                        cval = lines[i+1];
                    } else if (lowerLine === 'type' && lines[i+1]) {
                        type_name = lines[i+1];
                        if (type_name.toLowerCase().includes('elc')) lvl = 'ELC';
                    } else if ((lowerLine === 'total' || lowerLine === 'total value') && (!cval || cval === '0') && lines[i+1]) {
                        cval = lines[i+1];
                    }
                }

                // Запасной план: если текст сплошной, без переносов
                if (len === '1' && cval === '0') {
                    const words = rawText.split(/\\s+/);
                    words.forEach((w, i) => {
                        if ((w.toLowerCase() === 'length' || w.toLowerCase() === 'term') && words[i+1]) len = words[i+1];
                        if ((w.toLowerCase() === 'hit' || w.toLowerCase() === 'aav') && words[i+1]) cval = words[i+1];
                    });
                }

                const fullText = rawText.toLowerCase();
                if (!type_name && fullText.includes('extension')) type_name = 'Extension';
                if (!lvl && fullText.includes('elc')) lvl = 'ELC';
                
                results.push({
                    p_fn: parts[0] || '',
                    p_ln: parts.slice(1).join(' ') || '',
                    team_name: team_name,
                    cval: cval,
                    len: len,
                    lvl: lvl,
                    type_name: type_name
                });
                
                if (results.length >= 5) break;
            }
            
            return results;
        }""")

        # --- СБОР ТРЕЙДОВ ---
        print("Загрузка страницы трейдов...")
        try:
            await page.goto("https://puckpedia.com/trades", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector('div[x-html="row.details_nolinks"]', timeout=15000)
        except Exception as e:
            print(f"Предупреждение по трейдам: {e}")
        
        all_trades = await page.evaluate("""() => {
            const blocks = Array.from(document.querySelectorAll('div[x-html="row.details_nolinks"]'));
            return blocks.map(el => el.innerText.trim());
        }""")
        
        trades = [translate_trade(t) for t in all_trades if "The ID of this channel" not in t and len(t) > 20]
        
        await browser.close()

    if not extracted_signings and not trades:
        print("Внимание: Никакие данные не собрались из HTML структуры. Операция прервана.")
        return

    print(f"Успешно собрано. Подписаний: {len(extracted_signings)}, Трейдов: {len(trades)}")

    # --- ФОРМИРОВАНИЕ ТЕКСТА И КЭШИРОВАНИЕ ---
    s_list = []
    current_signature_elements = []

    for item in extracted_signings[:3]:
        first_name = re.sub(r'<[^>]+>', '', str(item.get('p_fn', ''))).strip()
        last_name = re.sub(r'<[^>]+>', '', str(item.get('p_ln', ''))).strip()
        name = f"{first_name} {last_name}".strip()
        if not name: continue
        
        current_signature_elements.append(name)
        
        lvl = str(item.get("lvl", "")).upper()
        
        raw_cval = str(item.get('cval', 0) or 0)
        try:
            clean_cval = re.sub(r'[^0-9.]', '', raw_cval)
            if 'm' in raw_cval.lower() or 'м' in raw_cval.lower():
                total_val = float(clean_cval) * 1000000
            else:
                total_val = float(clean_cval) if clean_cval else 0
        except:
            total_val = 0
            
        raw_len = str(item.get('len', '1'))
        try:
            years_match = re.search(r'\d+', raw_len)
            years = int(years_match.group()) if years_match else 1
        except:
            years = 1
            
        # Используем значение напрямую (без деления), так как сайт отдает готовый CAP HIT
        cap_val = total_val
        
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
