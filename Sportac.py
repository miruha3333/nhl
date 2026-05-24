import asyncio
import os
import re
import requests
from playwright.async_api import async_playwright

# --- НАСТРОЙКИ ---
# Для получения аббревиатур (как было раньше)
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

# Новый словарь для перевода команд на русский
RUS_TEAM_MAPPING = {
    'Buffalo Sabres': 'Баффало (обменяли)', 'Carolina Hurricanes': 'Каролина (обменяла)',
    'Boston Bruins': 'Бостон (обменял)', 'Columbus Blue Jackets': 'Коламбус (обменял)',
    'Detroit Red Wings': 'Детройт (обменял)', 'New Jersey Devils': 'Нью-Джерси (обменяли)',
    'Montreal Canadiens': 'Монреаль (обменял)', 'New York Islanders': 'Айлендерс (обменял)',
    'Ottawa Senators': 'Оттава (обменяла)', 'New York Rangers': 'Рейнджерс (обменяли)',
    'Tampa Bay Lightning': 'Тампа (обменяла)', 'Philadelphia Flyers': 'Филадельфия (обменяла)',
    'Toronto Maple Leafs': 'Торонто (обменяло)', 'Pittsburgh Penguins': 'Питтсбург (обменял)',
    'Florida Panthers': 'Флорида (обменяла)', 'Washington Capitals': 'Вашингтон (обменял)',
    'Chicago Blackhawks': 'Чикаго (обменяло)', 'Anaheim Ducks': 'Анахайм (обменял)',
    'Colorado Avalanche': 'Колорадо (обменяло)', 'Calgary Flames': 'Калгари (обменяли)',
    'Dallas Stars': 'Даллас (обменял)', 'Edmonton Oilers': 'Эдмонтон (обменял)',
    'Minnesota Wild': 'Миннесота (обменяла)', 'Los Angeles Kings': 'Лос-Анджелес (обменял)',
    'Nashville Predators': 'Нэшвилл (обменял)', 'San Jose Sharks': 'Сан-Хосе (обменяло)',
    'St. Louis Blues': 'Сент-Луис (обменял)', 'Seattle Kraken': 'Сиэттл (обменял)',
    'Utah Mammoth': 'Юта (обменяла)', 'Vancouver Canucks': 'Ванкувер (обменял)',
    'Winnipeg Jets': 'Виннипег (обменял)'
}

def translate_rus_team(eng_name):
    # Поиск ключа по частичному совпадению
    for eng_key, rus_val in RUS_TEAM_MAPPING.items():
        if eng_name.lower().strip() in eng_key.lower():
            return rus_val
    return eng_name # Если не нашли в словаре

def translate_trade(text):
    if "forfeit" in text.lower(): return text
    # Регулярка захватывает: Team1, Players1, Team2, Players2
    pattern = r"The (.+?) acquire (.+?) from the (.+?) for (.+)"
    match = re.search(pattern, text)
    if match:
        team1, p1, team2, p2 = match.groups()
        
        rus_t1 = translate_rus_team(team1)
        rus_t2 = translate_rus_team(team2)
        
        p1 = p1.replace(".", "").replace(" and ", " и ")
        p2 = p2.replace(".", "").replace(" and ", " и ")
        
        return f"{rus_t1} {p2} на {p1} из {team2.replace(team2, rus_t2.split('(')[0].strip())}"
    return text

# ... (остальные функции send_to_telegram, format_years, format_cap_hit остаются без изменений)

# --- ФОРМИРОВАНИЕ ---
# Внутри main() обновленный вывод:
# ...
    s_list = []
    for item in extracted_signings[:3]:
        # ... (логика расчета Cap Hit)
        line = f"{name} {ctype} {format_years(years)} с кэпхитом {format_cap_hit(cap_val)} {get_team_abbr(item.get('team_name'))}"
        s_list.append(line)
        
    t_list = [translate_trade(t) for t in trades[:3]]

    # Финальный вывод с пустой строкой и без точек
    message = f"🔥 3 ПОСЛЕДНИХ ПОДПИСАНИЯ:\n\n{chr(10).join(s_list)}\n\n🤝 3 ПОСЛЕДНИХ ТРЕЙДА:\n\n{chr(10).join(t_list)}"
