import os
from dotenv import load_dotenv
load_dotenv()  # Загружает переменные из .env файла (только для локальной разработки)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Значение берётся из переменной окружения
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
# ... остальной код config.py
