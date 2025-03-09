#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from db.database import save_event_to_db, save_event_to_elasticsearch
from telegram.bot import send_telegram_notification
from utils.env_loader import load_config_with_env

# Создаем логгер
logger = logging.getLogger('server.api')

# Создаем роутер
router = APIRouter(prefix="/api", tags=["events"])

# Схема для проверки API ключа
API_KEY_HEADER = APIKeyHeader(name="Authorization")

# Загружаем конфигурацию для получения API ключа
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config', 'config.yaml')
try:
    config = load_config_with_env(config_path)
    API_KEY = config['api']['key']
except Exception as e:
    logger.error(f"Ошибка при загрузке API ключа: {str(e)}")
    API_KEY = "your_api_key_here"  # Значение по умолчанию

# Модель данных для события
class EventModel(BaseModel):
    timestamp: str
    username: str
    process_name: str
    pid: int

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """Проверка API ключа"""
    if not api_key.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный формат API ключа"
        )
    
    # Извлекаем ключ из заголовка
    key = api_key.replace("Bearer ", "")
    
    # Проверяем ключ из конфигурации
    if key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный API ключ"
        )
    
    return key

@router.post("/events", status_code=status.HTTP_200_OK)
async def create_event(event: EventModel, request: Request, api_key: str = Depends(verify_api_key)):
    """Обработка события от агента"""
    try:
        # Получаем IP-адрес агента
        client_host = request.client.host
        
        # Логируем получение события
        logger.info(f"Получено событие от {client_host}: {event.process_name}")
        
        # Сохраняем событие в PostgreSQL
        db_result = save_event_to_db(event)
        
        # Сохраняем событие в Elasticsearch
        es_result = save_event_to_elasticsearch(event)
        
        # Отправляем уведомление в Telegram
        telegram_result = send_telegram_notification(event)
        
        # Возвращаем результат
        return {
            "status": "success",
            "message": "Событие успешно обработано",
            "event_id": db_result
        }
    except Exception as e:
        logger.error(f"Ошибка при обработке события: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обработке события: {str(e)}"
        )

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Проверка работоспособности сервера"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    } 