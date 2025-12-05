import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Moscow')

# Даты календаря
DATES = [
    '17.12.2025',
    '18.12.2025', 
    '19.12.2025',
    '22.12.2025',
    '23.12.2025',
    '24.12.2025',
    '25.12.2025'
]

# Времена
SEND_TIME = "18:00"  # Время рассылки
DEADLINE_TIME = "20:00"  # Дедлайн
CHECK_DEADLINE_TIME = "20:01"  # Проверка дедлайнов

# Имена листов в Google Таблице
SHEET_NAMES = {
    'users': 'Участники',
    'tasks': 'Задания_база',
    'schedules': 'Расписания',
    'progress': 'Прогресс',
    'config': 'Конфиг'
}
