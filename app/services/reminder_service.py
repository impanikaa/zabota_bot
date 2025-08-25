from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, time, timedelta
from sqlalchemy import func
import json
import random
import pytz
import asyncio
import logging
import threading

from app.db.session import Session
from app.db.models import UserReminder, Quote, ReminderStat
from app.config import BOT_TOKEN
from aiogram import Bot

# Создаем бота глобально
bot = Bot(token=BOT_TOKEN)
# Используем AsyncIOScheduler для асинхронной работы
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
msk_tz = pytz.timezone('Europe/Moscow')

# Настройка логирования
logger = logging.getLogger(__name__)

# Флаг для отслеживания состояния планировщика
scheduler_lock = threading.Lock()
scheduler_initialized = False


def init_scheduler():
    """Инициализация планировщика"""
    global scheduler_initialized

    with scheduler_lock:
        if scheduler_initialized:
            return

        try:
            # Останавливаем планировщик, если он уже запущен
            if scheduler.running:
                scheduler.shutdown(wait=False)

            # Запускаем планировщик
            scheduler.start()
            logger.info("Scheduler initialized successfully")

            # Загружаем все активные напоминания
            load_reminders()

            scheduler_initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")


def load_reminders():
    """Загружает все активные напоминания в планировщик"""
    try:
        with Session() as session:
            reminders = session.query(UserReminder).filter_by(is_active=True).all()
            for reminder in reminders:
                schedule_reminder(reminder)
            logger.info(f"Loaded {len(reminders)} reminders into scheduler")
    except Exception as e:
        logger.error(f"Failed to load reminders: {e}")


def schedule_reminder(reminder):
    """Планирует напоминание в scheduler"""
    try:
        # Удаляем старые job'ы для этого напоминания
        remove_reminder(reminder.id)

        if reminder.schedule_type == 'fixed':
            times = json.loads(reminder.times)
            for time_str in times:
                hour, minute = map(int, time_str.split(':'))

                # Создаем время напоминания
                reminder_time = datetime.now(msk_tz).replace(hour=hour, minute=minute, second=0, microsecond=0)

                # Если время уже прошло сегодня, планируем на завтра
                if reminder_time < datetime.now(msk_tz):
                    reminder_time += timedelta(days=1)

                trigger = CronTrigger(
                    hour=reminder_time.hour,
                    minute=reminder_time.minute,
                    timezone='Europe/Moscow'
                )

                scheduler.add_job(
                    async_send_reminder,
                    trigger,
                    args=[reminder.id],
                    id=f"reminder_{reminder.id}_{time_str}",
                    misfire_grace_time=3600,
                    coalesce=True
                )
                logger.info(f"Scheduled reminder {reminder.id} for {reminder_time.strftime('%H:%M')}")
        elif reminder.schedule_type == 'interval':
            trigger = IntervalTrigger(hours=reminder.interval_hours, timezone='Europe/Moscow')
            scheduler.add_job(
                async_send_reminder,
                trigger,
                args=[reminder.id],
                id=f"reminder_{reminder.id}_interval",
                misfire_grace_time=3600,
                coalesce=True
            )
            logger.info(f"Scheduled interval reminder {reminder.id} every {reminder.interval_hours} hours")
        elif reminder.schedule_type == 'random':
            # Для случайного расписания генерируем случайное время в пределах интервала
            next_run_time = generate_random_time(reminder)
            trigger = DateTrigger(run_date=next_run_time)

            scheduler.add_job(
                async_send_reminder,
                trigger,
                args=[reminder.id],
                id=f"reminder_{reminder.id}_random_{next_run_time.timestamp()}",
                misfire_grace_time=3600,
                coalesce=True
            )
            logger.info(f"Scheduled random reminder {reminder.id} for {next_run_time}")
    except Exception as e:
        logger.error(f"Failed to schedule reminder {reminder.id}: {e}")


def generate_random_time(reminder):
    """Генерирует случайное время для напоминания в пределах интервала"""
    now = datetime.now(msk_tz)

    # Определяем интервал в секундах
    interval_seconds = reminder.random_interval_hours * 3600

    # Генерируем случайное смещение в пределах интервала
    random_offset = random.randint(0, interval_seconds)

    # Вычисляем следующее время выполнения
    next_run_time = now + timedelta(seconds=random_offset)

    # Если установлено тихое время, проверяем не попадает ли в него
    if reminder.start_time and reminder.end_time:
        start_hour, start_minute = map(int, reminder.start_time.split(':'))
        end_hour, end_minute = map(int, reminder.end_time.split(':'))

        # Создаем временные объекты
        quiet_start = time(start_hour, start_minute)
        quiet_end = time(end_hour, end_minute)

        # Получаем время следующего выполнения
        next_run_time_time = next_run_time.time()

        # Проверяем, попадает ли в тихое время
        if quiet_start < quiet_end:
            # Тихое время не пересекает полночь
            is_quiet_time = quiet_start <= next_run_time_time <= quiet_end
        else:
            # Тихое время пересекает полночь (например, 23:00-06:00)
            is_quiet_time = next_run_time_time >= quiet_start or next_run_time_time <= quiet_end

        # Если попадает в тихое время, корректируем
        if is_quiet_time:
            if quiet_start < quiet_end:
                # Добавляем время до конца тихого периода
                quiet_end_dt = datetime.combine(next_run_time.date(), quiet_end)
                if next_run_time < quiet_end_dt:
                    next_run_time = quiet_end_dt
                else:
                    next_run_time = quiet_end_dt + timedelta(days=1)
            else:
                # Тихое время пересекает полночь
                if next_run_time_time >= quiet_start:
                    # Текущее время после начала тихого времени
                    quiet_end_dt = datetime.combine(next_run_time.date() + timedelta(days=1), quiet_end)
                    next_run_time = quiet_end_dt
                else:
                    # Текущее время до окончания тихого времени
                    quiet_end_dt = datetime.combine(next_run_time.date(), quiet_end)
                    next_run_time = quiet_end_dt

    return next_run_time


async def async_send_reminder(reminder_id):
    """Асинхронная обертка для отправки напоминания"""
    logger.info(f"Starting to send reminder {reminder_id}")
    try:
        await send_reminder(reminder_id)
    except Exception as e:
        logger.error(f"Error in async_send_reminder for {reminder_id}: {e}")


async def send_reminder(reminder_id):
    """Отправляет напоминание"""
    try:
        with Session() as session:
            reminder = session.query(UserReminder).get(reminder_id)
            if not reminder or not reminder.is_active:
                logger.warning(f"Reminder {reminder_id} not found or inactive")
                return

            # Проверяем, не тихое ли сейчас время (только если установлено тихое время)
            if reminder.start_time and reminder.end_time:
                now = datetime.now(msk_tz)
                current_time = now.time()

                start = time(*map(int, reminder.start_time.split(':')))
                end = time(*map(int, reminder.end_time.split(':')))

                # Логика для времени, которое переходит через полночь (23:00-06:00)
                if start < end:
                    # Обычный интервал в пределах одних суток
                    is_quiet_time = start <= current_time <= end
                else:
                    # Интервал переходит через полночь (например, 23:00-06:00)
                    is_quiet_time = current_time >= start or current_time <= end

                if is_quiet_time:
                    # Записываем в статистику пропуск из-за тихого времени
                    stat = ReminderStat(
                        reminder_id=reminder.id,
                        status='skipped_quiet_time'
                    )
                    session.add(stat)
                    session.commit()
                    logger.info(f"Skipped reminder {reminder.id} due to quiet time")

                    # Для случайных напоминаний планируем следующее
                    if reminder.schedule_type == 'random':
                        schedule_reminder(reminder)
                    return

            # Формируем сообщение
            if reminder.type == 'habit':
                if reminder.habit_type:
                    # Предустановленная привычка
                    habits = {
                        "water": "💧 Не забудь выпить стакан воды!",
                        "posture": "🧘 Проверь свою осанку!",
                        "eyes": "👀 Сделай перерыв и зарядку для глаз",
                        "stretch": "🔁 Пора размяться и потянуться!"
                    }
                    text = habits[reminder.habit_type]
                else:
                    text = f"🏃 Напоминание: {reminder.custom_text}"
            else:
                # Случайная цитата из всей базы
                quote = session.query(Quote).filter_by(is_active=True).order_by(func.random()).first()
                text = f"💬 {quote.text}" if quote else "💬 Помни, что ты молодец!"

            # Отправляем сообщение
            await bot.send_message(reminder.user_id, text)

            # Записываем в статистику успешную отправку
            stat = ReminderStat(
                reminder_id=reminder.id,
                status='sent'
            )
            session.add(stat)
            session.commit()

            logger.info(f"Sent reminder {reminder.id} to user {reminder.user_id}")

            # Для случайных напоминаний планируем следующее
            if reminder.schedule_type == 'random':
                schedule_reminder(reminder)

    except Exception as e:
        logger.error(f"Failed to send reminder {reminder_id}: {e}")

        # Записываем в статистику ошибку
        try:
            with Session() as session:
                stat = ReminderStat(
                    reminder_id=reminder_id,
                    status='error'
                )
                session.add(stat)
                session.commit()
        except Exception as inner_e:
            logger.error(f"Failed to save error stat: {inner_e}")


def remove_reminder(reminder_id):
    """Удаляет все job'ы для этого напоминания"""
    try:
        jobs = scheduler.get_jobs()
        for job in jobs:
            if job.id.startswith(f"reminder_{reminder_id}"):
                scheduler.remove_job(job.id)
                logger.info(f"Removed job {job.id} for reminder {reminder_id}")
    except Exception as e:
        logger.error(f"Failed to remove reminder {reminder_id}: {e}")


# Инициализируем планировщик при импорте модуля
init_scheduler()