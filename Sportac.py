import time
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os

# Твой эталонный словарь сокращений команд
TEAM_MAPPING = {
    'utah': 'UTAH',
    'mammoth': 'UTAH',
    'blue jackets': 'CBJ',
    'bluejackets': 'CBJ',
    'predators': 'NAS',
    'ducks': 'ANA',
    'jets': 'WPG',
    'wild': 'MIN',
    'islanders': 'NYI',
    'rangers': 'NYR',
    'kings': 'LAK',
    'sabres': 'BUF',
    'blackhawks': 'CHI',
    'golden knights': 'VGK',
    'goldenknights': 'VGK',
    'canucks': 'VAN',
    'flyers': 'PHI', 
    'bruins': 'BOS', 
    'sharks': 'SJS', 
    'hurricanes': 'CAR',
    'penguins': 'PIT', 
    'capitals': 'WSH', 
    'canadiens': 'MTL', 
    'senators': 'OTT', 
    'red wings': 'DET', 
    'redwings': 'DET', 
    'maple leafs': 'TOR', 
    'mapleleafs': 'TOR', 
    'oilers': 'EDM', 
    'panthers': 'FLA',
    'lightning': 'TBL', 
    'stars': 'DAL', 
    'avalanche': 'COL',
    'devils': 'NJD',
    'kraken': 'SEA',
    'flames': 'CGY',
    'blues': 'STL'
}

def get_team_abbr(img_src):
    if not img_src:
        return ""
    src_lower = img_src.lower()
    for team_key, abbr in TEAM_MAPPING.items():
        if team_key in src_lower:
            return f"({abbr})"
    
    match = re.search(r'nhl_([a-z0-9]+)\.', src_lower)
    if match:
        raw_abbr = match.group(1)
        if raw_abbr == "vgs": return "(VGK)"
        if raw_abbr == "sj": return "(SJS)"
        if raw_abbr == "nj": return "(NJD)"
        return f"({raw_abbr.upper()})"
    return ""

def get_years_string(years_str):
    try:
        y = int(years_str)
        if y == 1: return "1 год"
        elif 2 <= y <= 4: return f"{y} года"
        else: return f"{y} лет"
    except: 
        return f"{years_str} лет"

def translate_action(text, team_abbr):
    text = re.sub(r'\([A-Z]{2,4}\)', '', text).strip()
    
    # 1А. Контракты тренеров (БЕЗ указания суммы $, например у Линди Раффа)
    coach_contract_match = re.search(r'Signed a (\d+) year contract (extension )?with', text, re.IGNORECASE)
    if coach_contract_match:
        years_num = coach_contract_match.group(1)
        is_extension = coach_contract_match.group(2)
        action_verb = "продлил контракт" if is_extension else "подписал контракт"
        years_txt = get_years_string(years_num)
        return f"{action_verb} на {years_txt} {team_abbr}"

    # 1Б. Стандартные контракты игроков (С указанием суммы $)
    contract_match = re.search(r'Signed a (\d+) year \$([\d\.,]+)( million)? contract (extension )?with', text, re.IGNORECASE)
    if contract_match:
        years_num = contract_match.group(1)
        money = contract_match.group(2)
        is_million = contract_match.group(3)
        is_extension = contract_match.group(4)
        action_verb = "продлил контракт" if is_extension else "подписал контракт"
        years_txt = get_years_string(years_num)
        money_suffix = " млн." if is_million else ""
        return f"{action_verb}, {years_txt}, ${money}{money_suffix} {team_abbr}"
    
    # 2. Фарм-клубы (Minors)
    if "Demoted to the Minors" in text:
        return f"отправлен в фарм-клуб {team_abbr}"
    if "Promoted from the Minors" in text:
        return f"вызван из фарм-клуба {team_abbr}"
    
    # 3. Увольнения и найм
    if "Fired by" in text: return f"уволен {team_abbr}"
    if "Hired as" in text or "Hired by" in text: return f"нанят {team_abbr}"
    
    # 4. Штрафы
    fine_match = re.search(r'Fined \$([\d,]+)', text)
    if fine_match: return f"оштрафован на ${fine_match.group(1)} {team_abbr}"
    
    # 5. Дисквалификации
    susp_match = re.search(r'Suspended (\d+) game', text, re.IGNORECASE)
    if susp_match: 
        games_num = int(susp_match.group(1))
        games_txt = "1 игру" if games_num == 1 else f"{games_num} матчей"
        return f"дисквалифицирован на {games_txt} {team_abbr}"

    return f"{text} {team_abbr}"

def parse_spotrac_final():
    print("Запуск парсера Spotrac (Фильтрация дат в именах и контракты тренеров)...")
    os.system("pkill -f chrome")

    options = uc.ChromeOptions()
    options.headless = False 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=148)
        driver.get("https://www.spotrac.com/nhl/transactions/")
        time.sleep(15)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        items = soup.find_all('li', class_='list-group-item')

        if items:
            now = datetime.now()
            five_days_ago = now - timedelta(days=5)
            output_lines = []

            for item in items:
                team_abbr = ""
                img = item.find('img', src=re.compile(r'nhl_'))
                if img and img.get('src'):
                    team_abbr = get_team_abbr(img.get('src'))

                full_text = " ".join(item.get_text().split())
                date_match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', full_text)
                
                if date_match:
                    try:
                        event_date = datetime.strptime(date_match.group(1), '%B %d, %Y')
                        if event_date >= five_days_ago:
                            header = full_text.split(" - ")[0]
                            
                            # Очищаем имя от (COA) и прочих скобок
                            name_part = re.sub(r'\(COA\)', '', header).strip()
                            name_part = name_part.split('(')[0].strip()
                            
                            # Вырезаем текстовую дату из имени тренера/игрока
                            name_part = re.sub(r'[A-Z][a-z]+\s+\d{1,2},\s+\d{4}', '', name_part).strip()
                            
                            action_raw = full_text.split(" - ")[1] if " - " in full_text else ""
                            action_translated = translate_action(action_raw, team_abbr)
                            
                            # Форматируем вывод: убираем запятую для увольнений, найма и контрактов без ценника (как у тренеров)
                            if any(x in action_translated for x in ["уволен", "нанят", "продлил контракт на", "подписал контракт на"]):
                                result_line = f"{name_part} {action_translated}"
                            else:
                                result_line = f"{name_part}, {action_translated}"
                            
                            print(result_line)
                            output_lines.append(result_line)
                    except: 
                        continue

            if output_lines:
                with open("/home/miha/nhl_transactions.txt", "w", encoding="utf-8") as f:
                    f.write("\n".join(output_lines))
                print("\n[УСПЕХ] Файл nhl_transactions.txt обновлен.")
            else:
                print("\nТранзакций за последние 5 дней не найдено.")
    except Exception as e: 
        print(f"Ошибка: {e}")
    finally:
        if driver: 
            driver.quit()

if __name__ == "__main__":
    parse_spotrac_final()
