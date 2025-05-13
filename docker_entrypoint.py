#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
import argparse
import signal
import subprocess
from pathlib import Path

# Настраиваем пути для работы в Docker-контейнере
APP_DIR = Path('/app')
CONFIG_PATH = APP_DIR / 'config.json'
ENV_PATH = APP_DIR / '.env'
LOGS_DIR = APP_DIR / 'logs'
DATA_DIR = APP_DIR / 'data'

# Добавляем директорию проекта в путь импорта
sys.path.append(str(APP_DIR))

# Пытаемся импортировать функции из модуля src.agent
try:
    from src.agent import find_and_load_env, find_config_file, load_config, check_required_env_vars
except ImportError:
    print("Не удалось импортировать модуль src.agent")
    sys.exit(1)

def setup_logging():
    """Настройка логирования"""
    logger = logging.getLogger('DockerAgent')
    logger.setLevel(logging.INFO)
    
    # Создаем директорию для логов, если она не существует
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Обработчик для вывода в файл
    file_handler = logging.FileHandler(LOGS_DIR / 'docker_agent.log')
    file_handler.setLevel(logging.INFO)
    
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Формат логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def check_wsl_env():
    """Проверка запуска в среде WSL"""
    # Проверяем характерные признаки WSL
    return os.path.exists('/proc/sys/fs/binfmt_misc/WSLInterop')

def prepare_environment():
    """Подготовка окружения для запуска в Docker"""
    logger = logging.getLogger('DockerAgent')
    
    # Создаем необходимые директории
    LOGS_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    
    # Проверяем наличие конфигурационного файла
    if not CONFIG_PATH.exists():
        logger.error(f"Конфигурационный файл не найден: {CONFIG_PATH}")
        sys.exit(1)
    
    # Проверяем наличие .env файла
    env_path = find_and_load_env()
    if env_path:
        logger.info(f"Загружены переменные окружения из {env_path}")
    else:
        logger.warning("Файл .env не найден")
        
        # Если есть пример .env файла, создаем из него .env
        example_path = APP_DIR / 'dotenv.example'
        if example_path.exists():
            import shutil
            shutil.copy(example_path, ENV_PATH)
            logger.info(f"Создан файл .env из {example_path}")
            # Перезагружаем переменные окружения
            find_and_load_env()
    
    # Проверяем конфигурацию
    try:
        config = load_config(CONFIG_PATH)
        
        # Проверяем, запущены ли мы в WSL
        is_wsl = check_wsl_env()
        if is_wsl:
            logger.info("Обнаружена среда WSL")
            # Устанавливаем флаг WSL в конфигурации
            if 'docker' in config:
                config['docker']['wsl'] = True
                
            # Проверяем доступ к Windows Event Logs
            evtx_path = Path('/winevt/Logs')
            if not evtx_path.exists():
                logger.warning(f"Путь к Windows Event Logs не найден: {evtx_path}")
                logger.warning("Убедитесь, что том смонтирован корректно из WSL")
        
        missing_vars = check_required_env_vars(config)
        if missing_vars:
            logger.error(f"Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
            logger.error("Обновите файл .env или config.json перед запуском агента")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка при загрузке конфигурации: {e}")
        sys.exit(1)
    
    logger.info("Окружение успешно подготовлено")
    return config

def run_agent(config):
    """Запуск агента мониторинга"""
    logger = logging.getLogger('DockerAgent')
    logger.info("Запуск агента мониторинга...")
    
    # Путь к скрипту агента
    main_script = APP_DIR / 'src' / 'agent' / 'main.py'
    
    if not main_script.exists():
        logger.error(f"Скрипт агента не найден: {main_script}")
        sys.exit(1)
    
    # Формируем команду для запуска агента
    cmd = [sys.executable, str(main_script), "--config", str(CONFIG_PATH), "--log-dir", str(LOGS_DIR)]
    
    try:
        # Запускаем процесс
        process = subprocess.Popen(cmd)
        logger.info(f"Агент запущен с PID {process.pid}")
        
        # Функция для обработки сигналов
        def signal_handler(sig, frame):
            logger.info(f"Получен сигнал {sig}, завершение работы...")
            process.terminate()
            sys.exit(0)
        
        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Ожидаем завершения процесса
        while True:
            if process.poll() is not None:
                logger.error(f"Процесс агента завершился с кодом {process.returncode}")
                logger.info("Перезапуск агента через 5 секунд...")
                time.sleep(5)
                process = subprocess.Popen(cmd)
                logger.info(f"Агент перезапущен с PID {process.pid}")
            time.sleep(1)
    except Exception as e:
        logger.error(f"Ошибка запуска агента: {e}")
        sys.exit(1)

def main():
    """Основная функция"""
    logger = setup_logging()
    logger.info("Запуск Docker-контейнера Windows Monitor Agent")
    
    # Подготовка окружения
    config = prepare_environment()
    
    # Запуск агента
    run_agent(config)

if __name__ == "__main__":
    main() 