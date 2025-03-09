#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import asyncio
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

# Создаем логгер
logger = logging.getLogger('server.telegram')

# Глобальная переменная для бота
telegram_bot = None
telegram_chat_id = None

def init_telegram_bot(config):
    """Инициализация Telegram бота"""
    global telegram_bot, telegram_chat_id
    
    try:
        # Получаем настройки из конфигурации
        bot_token = config['telegram']['bot_token']
        telegram_chat_id = config['telegram']['chat_id']
        
        # Создаем экземпляр бота
        telegram_bot = Bot(token=bot_token)
        
        # Проверяем соединение, отправляя тестовое сообщение
        asyncio.run(telegram_bot.send_message(
            chat_id=telegram_chat_id,
            text="🟢 Сервер мониторинга запущен и готов к работе"
        ))
        
        logger.info("Telegram бот успешно инициализирован")
    except Exception as e:
        logger.error(f"Ошибка при инициализации Telegram бота: {str(e)}")
        raise

def send_telegram_notification(event):
    """Отправка уведомления в Telegram"""
    if not telegram_bot or not telegram_chat_id:
        logger.error("Telegram бот не инициализирован")
        return False
    
    try:
        # Преобразуем строку timestamp в объект datetime
        event_timestamp = datetime.fromisoformat(event.timestamp)
        
        # Форматируем время
        formatted_time = event_timestamp.strftime("%d.%m.%Y %H:%M:%S")
        
        # Формируем сообщение
        message = f"[{formatted_time}] Пользователь [{event.username}] запустил [{event.process_name}]"
        
        # Отправляем сообщение
        asyncio.run(telegram_bot.send_message(
            chat_id=telegram_chat_id,
            text=message
        ))
        
        logger.info(f"Уведомление отправлено в Telegram: {message}")
        return True
    except TelegramError as e:
        logger.error(f"Ошибка Telegram API при отправке уведомления: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления в Telegram: {str(e)}")
        return False 