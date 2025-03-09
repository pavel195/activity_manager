#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import yaml
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from db.database import init_db
from telegram.bot import init_telegram_bot
from utils.env_loader import load_config_with_env

def setup_logging(config):
    """Настройка логирования"""
    log_level = getattr(logging, config['logging']['level'])
    log_file = config['logging']['file']
    
    # Создаем директорию для логов, если она не существует
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('server')

def load_config():
    """Загрузка конфигурации из файла с обработкой переменных окружения"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.yaml')
    try:
        return load_config_with_env(config_path)
    except Exception as e:
        print(f"Ошибка при загрузке конфигурации: {e}")
        sys.exit(1)

def create_app(config):
    """Создание и настройка FastAPI приложения"""
    app = FastAPI(
        title="Monitoring Server API",
        description="API для приема данных от агентов мониторинга",
        version="1.0.0"
    )
    
    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Подключение маршрутов API
    app.include_router(api_router)
    
    return app

def main():
    """Основная функция сервера"""
    config = load_config()
    logger = setup_logging(config)
    
    logger.info("Сервер мониторинга запускается")
    
    # Инициализация базы данных
    init_db(config)
    
    # Инициализация Telegram бота
    init_telegram_bot(config)
    
    # Создание FastAPI приложения
    app = create_app(config)
    
    # Запуск сервера
    uvicorn.run(
        app,
        host=config['api']['host'],
        port=config['api']['port'],
        log_level="info" if not config['api']['debug'] else "debug"
    )
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 