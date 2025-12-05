import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEET_ID, SHEET_NAMES, DATES
import random
from datetime import datetime
import pytz

class GoogleSheets:
    def __init__(self):
        # Настройка доступа к Google Sheets
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(
            'credentials.json', 
            scopes=scopes
        )
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(GOOGLE_SHEET_ID)
        
    def get_worksheet(self, name):
        """Получить лист по имени"""
        return self.sheet.worksheet(SHEET_NAMES[name])
    
    def register_user(self, user_id, full_name):
        """Регистрация нового пользователя"""
        users_ws = self.get_worksheet('users')
        schedules_ws = self.get_worksheet('schedules')
        progress_ws = self.get_worksheet('progress')
        tasks_ws = self.get_worksheet('tasks')
        
        # Проверяем, есть ли уже пользователь
        try:
            users = users_ws.get_all_records()
            for user in users:
                if user.get('ФИО') == full_name:
                    # Обновляем Telegram ID если ФИО уже есть
                    row_idx = users.index(user) + 2
                    users_ws.update_cell(row_idx, 1, str(user_id))
                    users_ws.update_cell(row_idx, 2, full_name)
                    users_ws.update_cell(row_idx, 3, 'активен')
                    return f"Добро пожаловать обратно, {full_name}!"
        except Exception as e:
            print(f"Ошибка при проверке пользователя: {e}")
        
        # Добавляем нового пользователя
        users_ws.append_row([
            str(user_id), 
            full_name, 
            'активен',
            datetime.now().strftime('%d.%m.%Y')
        ])
        
        # Получаем все задания
        all_tasks = tasks_ws.get_all_records()
        task_ids = [task['ID_Задания'] for task in all_tasks]
        
        # Выбираем 7 уникальных случайных заданий
        if len(task_ids) < 7:
            return "Ошибка: В базе меньше 7 заданий"
        selected_tasks = random.sample(task_ids, 7)
        
        # Создаем расписание
        schedule_row = [str(user_id), full_name] + selected_tasks
        schedules_ws.append_row(schedule_row)
        
        # Создаем прогресс
        progress_row = [str(user_id), full_name, 0] + ['➖'] * 7 + [0]
        progress_ws.append_row(progress_row)
        
        return f"Регистрация успешна, {full_name}! Первое задание получите 16.12 в 18:00."
    
    def get_user_progress(self, user_id):
        """Получить прогресс пользователя"""
        progress_ws = self.get_worksheet('progress')
        all_progress = progress_ws.get_all_records()
        
        for progress in all_progress:
            if str(progress.get('ID_Участника', '')) == str(user_id):
                return progress
        return None
    
    def get_user_schedule(self, user_id):
        """Получить расписание пользователя"""
        schedules_ws = self.get_worksheet('schedules')
        all_schedules = schedules_ws.get_all_records()
        
        for schedule in all_schedules:
            if str(schedule.get('ID_Участника', '')) == str(user_id):
                return schedule
        return None
    
    def get_task_text(self, task_id):
        """Получить текст задания по ID"""
        tasks_ws = self.get_worksheet('tasks')
        all_tasks = tasks_ws.get_all_records()
        
        for task in all_tasks:
            if task.get('ID_Задания') == task_id:
                return task.get('Текст_задания', 'Задание не найдено')
        return "Задание не найдено"
    
    def mark_task_done(self, user_id):
        """Отметить задание как выполненное"""
        progress_ws = self.get_worksheet('progress')
        config_ws = self.get_worksheet('config')
        
        # Получаем текущий индекс
        config = config_ws.get_all_records()
        if not config:
            return "Календарь еще не начался"
        
        current_idx = config[0].get('Текущий_индекс', 0)
        
        if current_idx == 0:
            return "Календарь еще не начался"
        
        # Находим пользователя
        all_progress = progress_ws.get_all_values()
        user_row = None
        for i, row in enumerate(all_progress):
            if i == 0:  # Пропускаем заголовок
                continue
            if row[0] == str(user_id):
                user_row = i + 1
                break
        
        if not user_row:
            return "Пользователь не найден"
        
        # Проверяем статус текущего задания
        status_col = 3 + current_idx  # Смещение для статуса
        current_status = progress_ws.cell(user_row, status_col).value
        
        # Получаем текущее время
        tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz)
        deadline_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
        
        if current_status == '⏳':
            if now <= deadline_time:
                # Отмечаем как выполненное
                progress_ws.update_cell(user_row, status_col, '✅')
                
                # Увеличиваем счетчик выполненных
                done_count = int(progress_ws.cell(user_row, 11).value or 0)
                progress_ws.update_cell(user_row, 11, done_count + 1)
                
                return "✅ Задание отмечено как выполненное!"
            else:
                return "⏰ Время вышло! Задание уже нельзя отметить."
        elif current_status == '✅':
            return "✅ Это задание уже выполнено!"
        else:
            return "📭 Сейчас нет активного задания для отметки."
    
    def get_next_date(self):
        """Получить следующую дату для рассылки"""
        config_ws = self.get_worksheet('config')
        config = config_ws.get_all_records()
        if config:
            return config[0].get('Следующая_дата')
        return None
    
    def update_next_date(self):
        """Обновить следующую дату"""
        config_ws = self.get_worksheet('config')
        config = config_ws.get_all_records()
        
        if not config:
            # Инициализация
            config_ws.append_row(['Следующая_дата', 'Текущий_индекс', 'Дата_последней_рассылки'])
            config_ws.append_row(['17.12.2025', 0, ''])
        else:
            current_idx = config[0].get('Текущий_индекс', 0)
            
            if current_idx < len(DATES):
                # Обновляем индекс
                config_ws.update_cell(2, 2, current_idx + 1)
                
                if current_idx + 1 < len(DATES):
                    # Обновляем следующую дату
                    next_date = DATES[current_idx + 1]
                    config_ws.update_cell(2, 1, next_date)
    
    def get_all_active_users(self):
        """Получить всех активных пользователей"""
        users_ws = self.get_worksheet('users')
        users = users_ws.get_all_records()
        
        active_users = []
        for user in users:
            if user.get('Статус') == 'активен' and user.get('ID_Telegram'):
                active_users.append({
                    'id': user['ID_Telegram'],
                    'name': user['ФИО']
                })
        return active_users
    
    def update_task_status(self, user_id, date_index, status):
        """Обновить статус задания"""
        progress_ws = self.get_worksheet('progress')
        all_progress = progress_ws.get_all_values()
        
        for i, row in enumerate(all_progress):
            if i == 0:
                continue
            if row[0] == str(user_id):
                # Находим колонку для даты (даты начинаются с 3 колонки)
                status_col = 3 + date_index
                progress_ws.update_cell(i + 1, status_col, status)
                return True
        return False
    
    def get_config(self):
        """Получить конфигурацию"""
        config_ws = self.get_worksheet('config')
        config = config_ws.get_all_records()
        if config:
            return config[0]
        return None
