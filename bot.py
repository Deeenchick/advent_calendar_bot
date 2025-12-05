import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import *
from gsheets import GoogleSheets

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация Google Sheets
gsheets = GoogleSheets()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🎄 Привет, {user.first_name}!\n\n"
        "Я — бот для новогоднего Advent Calendar!\n\n"
        "📋 Для регистрации отправь мне своё **ФИО** (как в списке участников).\n\n"
        "После регистрации ты будешь получать ежедневные задания на 7 дней.\n"
        "Каждое задание нужно выполнить до 20:00 следующего дня.\n\n"
        "📌 Доступные команды:\n"
        "/start - начать регистрацию\n"
        "/расписание - показать твои задания\n"
        "/выполнено - отметить выполнение задания\n"
        "/статистика - топ участников\n"
        "/help - помощь"
    )

# Обработка ФИО для регистрации
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_name = update.message.text.strip()
    user_id = update.effective_user.id
    
    if len(full_name.split()) < 2:
        await update.message.reply_text("Пожалуйста, введите ФИО полностью (например, Иванов Иван Иванович)")
        return
    
    # Регистрируем пользователя
    result = gsheets.register_user(user_id, full_name)
    await update.message.reply_text(result)

# Команда /расписание
async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Получаем прогресс и расписание
    progress = gsheets.get_user_progress(user_id)
    schedule = gsheets.get_user_schedule(user_id)
    
    if not progress or not schedule:
        await update.message.reply_text("Вы не зарегистрированы. Используйте /start")
        return
    
    # Получаем конфигурацию
    config = gsheets.get_config()
    current_idx = config.get('Текущий_индекс', 0) if config else 0
    
    # Формируем сообщение
    message = "📅 **Ваш Advent Calendar 2025**\n\n"
    
    for i, date in enumerate(DATES):
        # Получаем ключ для колонки с датой
        date_key = f"Дата_{date.replace('.', '_')}"
        task_id = schedule.get(date_key) if schedule else None
        status_key = f"Статус_{date.replace('.', '_')}"
        status = progress.get(status_key, '➖') if progress else '➖'
        
        if i < current_idx:  # Прошедшие дни
            task_text = gsheets.get_task_text(task_id) if task_id else "Задание не найдено"
            message += f"**{date} [День {i+1}]**: {status}\n"
            if status == '✅':
                message += f"✅ Выполнено\n\n"
            elif status == '✖️':
                message += f"✖️ Просрочено\n\n"
        elif i == current_idx:  # Текущий день
            if task_id and status == '⏳':
                task_text = gsheets.get_task_text(task_id)
                message += f"**{date} [День {i+1}]**: ⏳ Активно\n"
                message += f"📝 *Задание*: {task_text}\n"
                message += f"⏰ *Срок*: до 20:00 сегодня\n\n"
            else:
                message += f"**{date} [День {i+1}]**: ➖ Ожидается\n\n"
        else:  # Будущие дни
            message += f"**{date} [День {i+1}]**: ➖ Сюрприз!\n\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

# Команда /выполнено
async def mark_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    result = gsheets.mark_task_done(user_id)
    await update.message.reply_text(result)

# Команда /статистика
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    progress_ws = gsheets.get_worksheet('progress')
    all_progress = progress_ws.get_all_records()
    
    # Сортируем по выполненным заданиям
    sorted_users = sorted(
        [p for p in all_progress if p.get('Всего_выполнено', 0) > 0],
        key=lambda x: x.get('Всего_выполнено', 0),
        reverse=True
    )[:5]  # Топ-5
    
    if not sorted_users:
        await update.message.reply_text("📊 Пока никто не выполнил заданий. Будьте первыми!")
        return
    
    message = "🏆 **Топ участников**\n\n"
    
    for i, user in enumerate(sorted_users):
        emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i] if i < 5 else "🏅"
        message += f"{emoji} {user['ФИО']} - {user['Всего_выполнено']} заданий\n"
    
    # Текущий день
    config = gsheets.get_config()
    if config and config.get('Текущий_индекс', 0) > 0:
        current_day = config.get('Текущий_индекс', 0)
        message += f"\n📆 *Текущий день: {current_day} из 7*"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ **Помощь**\n\n"
        "📋 **Регистрация:**\n"
        "1. Нажмите /start\n"
        "2. Отправьте боту своё ФИО\n\n"
        "📅 **Ежедневно:**\n"
        "• В 18:00 вы получите задание на завтра\n"
        "• До 20:00 нужно выполнить задание\n"
        "• Нажмите /выполнено для отметки\n\n"
        "📊 **Команды:**\n"
        "/расписание - ваши задания\n"
        "/выполнено - отметить выполнение\n"
        "/статистика - топ участников\n"
        "/help - эта справка"
    )

# Рассылка заданий
async def send_daily_tasks():
    """Рассылка заданий в 18:00"""
    logger.info("Запуск рассылки заданий...")
    
    # Получаем конфигурацию
    config = gsheets.get_config()
    if not config:
        logger.error("Конфигурация не найдена")
        return
    
    next_date = config.get('Следующая_дата')
    current_idx = config.get('Текущий_индекс', 0)
    
    # Проверяем, нужно ли сегодня рассылать
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).strftime('%d.%m.%Y')
    
    # Находим индекс даты в DATES
    try:
        date_index = DATES.index(next_date)
    except ValueError:
        logger.error(f"Дата {next_date} не найдена в списке DATES")
        return
    
    # Определяем дату рассылки (день перед заданием)
    if date_index > 0:
        send_date = DATES[date_index - 1]
    else:
        # Для первого дня рассылаем 16.12
        send_date = "16.12.2025"
    
    if today != send_date:
        logger.info(f"Сегодня {today}, а рассылка для {send_date}. Пропускаем.")
        return
    
    # Получаем всех активных пользователей
    users = gsheets.get_all_active_users()
    
    # Создаем временный объект Application для рассылки
    from telegram import Bot
    bot = Bot(token=TELEGRAM_TOKEN)
    
    for user in users:
        try:
            # Получаем задание пользователя
            schedule = gsheets.get_user_schedule(user['id'])
            if not schedule:
                continue
            
            # Получаем ключ для даты
            date_key = f"Дата_{next_date.replace('.', '_')}"
            task_id = schedule.get(date_key)
            if not task_id:
                continue
            
            task_text = gsheets.get_task_text(task_id)
            
            # Формируем сообщение
            message = (
                f"🎄 **Задание на завтра, {next_date}!**\n\n"
                f"📝 {task_text}\n\n"
                f"⏰ *Срок выполнения:* до 20:00 завтра\n"
                f"✅ Чтобы отметить выполнение, нажмите /выполнено\n\n"
                f"Удачи! 🎅"
            )
            
            # Обновляем статус задания
            gsheets.update_task_status(user['id'], date_index, '⏳')
            
            # Отправляем сообщение
            await bot.send_message(
                chat_id=user['id'],
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Отправлено задание пользователю {user['name']}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {user['name']}: {e}")
    
    # Обновляем следующую дату
    gsheets.update_next_date()
    logger.info(f"Рассылка для {next_date} завершена. Следующая дата обновлена.")

# Проверка дедлайнов
async def check_deadlines():
    """Проверка дедлайнов в 20:01"""
    logger.info("Проверка дедлайнов...")
    
    # Получаем конфигурацию
    config = gsheets.get_config()
    if not config or config.get('Текущий_индекс', 0) == 0:
        return
    
    current_idx = config.get('Текущий_индекс', 0)
    
    # Проверяем все активные задания для вчерашнего дня
    progress_ws = gsheets.get_worksheet('progress')
    all_progress = progress_ws.get_all_values()
    
    # Колонка для вчерашнего дня
    yesterday_col = 3 + (current_idx - 1)  # current_idx уже увеличен на 1
    
    updated = 0
    for i, row in enumerate(all_progress):
        if i == 0:  # Пропускаем заголовок
            continue
        
        if yesterday_col < len(row):
            status = row[yesterday_col]
            if status == '⏳':
                # Меняем на просрочено
                progress_ws.update_cell(i + 1, yesterday_col + 1, '✖️')
                updated += 1
    
    logger.info(f"Обновлено {updated} просроченных заданий")

# Основная функция
def main():
    """Запуск бота"""
    # Создаем Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("расписание", show_schedule))
    application.add_handler(CommandHandler("выполнено", mark_done))
    application.add_handler(CommandHandler("статистика", show_stats))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик текстовых сообщений (для ФИО)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_name
    ))
    
    # Настраиваем планировщик
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    
    # Задача на рассылку в 18:00
    scheduler.add_job(
        send_daily_tasks,
        CronTrigger(hour=18, minute=0, timezone=TIMEZONE)
    )
    
    # Задача на проверку дедлайнов в 20:01
    scheduler.add_job(
        check_deadlines,
        CronTrigger(hour=20, minute=1, timezone=TIMEZONE)
    )
    
    # Запускаем планировщик
    scheduler.start()
    
    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
