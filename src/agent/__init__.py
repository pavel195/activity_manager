"""
Windows Monitor Agent - модуль для мониторинга событий Windows
и отправки уведомлений в Telegram
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

def find_and_load_env():
    """
    Находит и загружает .env файл из возможных мест расположения
    Возвращает путь к найденному файлу или None
    """
    # Список возможных мест расположения .env файла
    possible_paths = [
        Path(".env"),  # Текущая директория
        Path(__file__).resolve().parent.parent.parent / ".env",  # Корневая директория проекта
        Path("C:/ProgramData/WindowsMonitor/.env"),  # Директория установки службы
        Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / "WindowsMonitor/.env"  # С использованием переменной окружения
    ]
    
    for env_path in possible_paths:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            return env_path
    
    return None

def find_config_file():
    """
    Находит конфигурационный файл в возможных местах расположения
    Возвращает путь к найденному файлу или None
    """
    # Возможные пути к конфигам
    config_paths = [
        Path("config.json"),
        Path(__file__).resolve().parent.parent.parent / "config.json",
        Path("C:/ProgramData/WindowsMonitor/config.json"),
        Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / "WindowsMonitor/config.json"
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            return config_path
    
    return None

def load_config(config_path=None):
    """
    Загружает конфигурацию из файла, объединяя с переменными окружения
    Если config_path не указан, пытается найти файл автоматически
    """
    if config_path is None:
        config_path = find_config_file()
        
    if config_path is None or not Path(config_path).exists():
        raise FileNotFoundError(f"Конфигурационный файл не найден")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Заменяем значения из переменных окружения
    if os.environ.get('TELEGRAM_TOKEN'):
        config['telegram_token'] = os.environ.get('TELEGRAM_TOKEN')
    
    if os.environ.get('CHAT_ID'):
        config['chat_id'] = os.environ.get('CHAT_ID')
    
    if os.environ.get('VT_API_KEY'):
        config['vt_api_key'] = os.environ.get('VT_API_KEY')
    
    return config

def check_required_env_vars(config):
    """
    Проверяет наличие обязательных переменных окружения или в конфиге
    Возвращает список отсутствующих переменных
    """
    required_vars = []
    
    # Проверяем наличие токена Telegram и chat_id
    if not config.get('telegram_token') and not os.environ.get('TELEGRAM_TOKEN'):
        required_vars.append('TELEGRAM_TOKEN')
    
    if not config.get('chat_id') and not os.environ.get('CHAT_ID'):
        required_vars.append('CHAT_ID')
    
    return required_vars 