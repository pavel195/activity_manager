#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import logging
import yaml
import json
import requests
import psutil
import getpass
from datetime import datetime

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
    return logging.getLogger('agent')

def load_config():
    """Загрузка конфигурации из файла с обработкой переменных окружения"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.yaml')
    try:
        return load_config_with_env(config_path)
    except Exception as e:
        print(f"Ошибка при загрузке конфигурации: {e}")
        sys.exit(1)

def get_running_processes():
    """Получение списка запущенных процессов"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'create_time']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes

def filter_monitored_processes(processes, monitored_processes):
    """Фильтрация процессов по списку отслеживаемых"""
    result = []
    for proc in processes:
        if proc['name'].lower() in [p.lower() for p in monitored_processes]:
            result.append(proc)
    return result

def send_event_to_server(event, config):
    """Отправка события на сервер"""
    url = config['server']['url']
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {config['server']['api_key']}"
    }
    
    try:
        response = requests.post(
            url, 
            json=event, 
            headers=headers, 
            timeout=config['server']['timeout']
        )
        if response.status_code == 200:
            return True, "Событие успешно отправлено"
        else:
            return False, f"Ошибка при отправке события: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Исключение при отправке события: {str(e)}"

def main():
    """Основная функция агента"""
    config = load_config()
    logger = setup_logging(config)
    
    logger.info("Агент мониторинга запущен")
    
    # Получаем имя пользователя
    username = getpass.getuser()
    
    # Словарь для хранения уже отправленных событий (чтобы не дублировать)
    sent_events = {}
    
    try:
        while True:
            current_processes = get_running_processes()
            monitored = filter_monitored_processes(current_processes, config['monitoring']['processes'])
            
            for proc in monitored:
                # Создаем уникальный ключ для процесса
                process_key = f"{proc['pid']}_{proc['name']}"
                
                # Если процесс уже был отправлен, пропускаем
                if process_key in sent_events:
                    continue
                
                # Формируем событие
                event = {
                    'timestamp': datetime.fromtimestamp(proc['create_time']).isoformat(),
                    'username': username,
                    'process_name': proc['name'],
                    'pid': proc['pid']
                }
                
                # Отправляем событие на сервер
                success, message = send_event_to_server(event, config)
                if success:
                    logger.info(f"Событие отправлено: {proc['name']} (PID: {proc['pid']})")
                    sent_events[process_key] = True
                else:
                    logger.error(message)
            
            # Очищаем словарь отправленных событий от процессов, которые уже не запущены
            current_pids = [f"{p['pid']}_{p['name']}" for p in current_processes]
            sent_events = {k: v for k, v in sent_events.items() if k in current_pids}
            
            # Пауза перед следующей проверкой
            time.sleep(config['monitoring']['interval'])
    except KeyboardInterrupt:
        logger.info("Агент мониторинга остановлен пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 