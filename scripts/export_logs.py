#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import logging
import datetime
import zipfile
import shutil
import win32evtlog
import win32evtlogutil
import win32con
from pathlib import Path
import json

# Добавляем директорию проекта в путь для импорта
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent
sys.path.append(str(project_root))

# Импорт функций из модуля src.agent
agent_module_available = False
try:
    from src.agent import find_and_load_env, find_config_file, load_config
    agent_module_available = True
except ImportError:
    pass  # Будет обработано далее

def setup_logging():
    logger = logging.getLogger('ExportLogs')
    logger.setLevel(logging.INFO)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Формат логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger

def export_windows_events(output_dir, event_logs=None, days=7):
    """Экспорт логов событий Windows в указанный каталог"""
    logger = logging.getLogger('ExportLogs')
    
    if event_logs is None:
        event_logs = ['System', 'Security', 'Application', 'Microsoft-Windows-Sysmon/Operational']
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    start_date = datetime.datetime.now() - datetime.timedelta(days=days)
    
    for log_name in event_logs:
        logger.info(f"Экспорт журнала событий: {log_name}")
        
        try:
            # Открываем журнал
            handle = win32evtlog.OpenEventLog(None, log_name)
            
            # Определяем общее количество событий
            total_records = win32evtlog.GetNumberOfEventLogRecords(handle)
            logger.info(f"Всего записей в журнале {log_name}: {total_records}")
            
            # Открываем файл для записи
            output_file = output_dir / f"{log_name.replace('/', '-')}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Экспорт журнала событий Windows: {log_name}\n")
                f.write(f"# Дата экспорта: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Период: последние {days} дней\n")
                f.write("# ==========================================\n\n")
                
                # Читаем события
                flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                events = win32evtlog.ReadEventLog(handle, flags, 0)
                
                event_count = 0
                
                while events:
                    for event in events:
                        # Проверяем дату события
                        event_date = event.TimeGenerated
                        
                        if event_date > start_date:
                            # Форматируем и записываем событие
                            f.write(f"Время: {event_date.strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"Источник: {event.SourceName}\n")
                            f.write(f"Тип: {event.EventType}\n")
                            f.write(f"Категория: {event.EventCategory}\n")
                            f.write(f"ID события: {event.EventID & 0xFFFF}\n")  # Нижние 16 бит - настоящий ID
                            
                            # Получаем описание события
                            try:
                                description = win32evtlogutil.SafeFormatMessage(event, log_name)
                                f.write(f"Описание: {description}\n")
                            except:
                                f.write("Описание: Не удалось получить описание\n")
                            
                            f.write("-" * 50 + "\n")
                            
                            event_count += 1
                    
                    # Читаем следующую порцию событий
                    events = win32evtlog.ReadEventLog(handle, flags, 0)
                
                # Закрываем журнал
                win32evtlog.CloseEventLog(handle)
                
                logger.info(f"Экспортировано {event_count} событий из журнала {log_name}")
                
        except Exception as e:
            logger.error(f"Ошибка при экспорте журнала {log_name}: {str(e)}")
    
    return output_dir

def export_agent_logs(output_dir, agent_log_dir=None, agent_data_dir=None):
    """Экспорт логов агента и данных о событиях в указанный каталог"""
    logger = logging.getLogger('ExportLogs')
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Копирование логов агента
    if agent_log_dir:
        agent_log_dir = Path(agent_log_dir)
        
        if agent_log_dir.exists():
            agent_logs_output = output_dir / "agent_logs"
            agent_logs_output.mkdir(exist_ok=True)
            
            logger.info(f"Копирование логов агента из {agent_log_dir}")
            
            log_files = list(agent_log_dir.glob("*.log"))
            
            for log_file in log_files:
                try:
                    shutil.copy(log_file, agent_logs_output)
                    logger.info(f"Скопирован файл: {log_file.name}")
                except Exception as e:
                    logger.error(f"Ошибка при копировании файла {log_file.name}: {str(e)}")
        else:
            logger.warning(f"Директория с логами агента не найдена: {agent_log_dir}")
    
    # Копирование данных о событиях
    if agent_data_dir:
        agent_data_dir = Path(agent_data_dir)
        events_dir = agent_data_dir / "events"
        
        if events_dir.exists():
            events_output = output_dir / "events_data"
            events_output.mkdir(exist_ok=True)
            
            logger.info(f"Копирование данных о событиях из {events_dir}")
            
            event_files = list(events_dir.glob("*.json"))
            
            for event_file in event_files:
                try:
                    # Копируем JSON-файл
                    shutil.copy(event_file, events_output)
                    
                    # Также создаем текстовое представление для удобства просмотра
                    txt_file = events_output / f"{event_file.stem}.txt"
                    
                    with open(event_file, 'r', encoding='utf-8') as f_in:
                        event_data = json.load(f_in)
                    
                    with open(txt_file, 'w', encoding='utf-8') as f_out:
                        f_out.write(f"# События за {event_file.stem}\n")
                        f_out.write("# ==========================================\n\n")
                        
                        # Запуски системы
                        f_out.write("## Запуски системы\n\n")
                        for event in event_data.get('startup', []):
                            f_out.write(f"Время: {event.get('time', 'Н/Д')}\n")
                            f_out.write(f"Описание: {event.get('description', 'Н/Д')}\n")
                            f_out.write("-" * 50 + "\n")
                        
                        # Входы пользователей
                        f_out.write("\n## Входы пользователей\n\n")
                        for event in event_data.get('login', []):
                            f_out.write(f"Время: {event.get('time', 'Н/Д')}\n")
                            f_out.write(f"Пользователь: {event.get('username', 'Н/Д')}\n")
                            f_out.write(f"Тип входа: {event.get('login_type', 'Н/Д')}\n")
                            f_out.write("-" * 50 + "\n")
                        
                        # Подозрительные процессы
                        f_out.write("\n## Подозрительные процессы\n\n")
                        for event in event_data.get('suspicious_process', []):
                            f_out.write(f"Время: {event.get('time', 'Н/Д')}\n")
                            f_out.write(f"Путь: {event.get('image', 'Н/Д')}\n")
                            f_out.write(f"Командная строка: {event.get('command_line', 'Н/Д')}\n")
                            f_out.write(f"Пользователь: {event.get('username', 'Н/Д')}\n")
                            f_out.write(f"Причина: {event.get('reason', 'Н/Д')}\n")
                            f_out.write("-" * 50 + "\n")
                    
                    logger.info(f"Обработан файл событий: {event_file.name}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке файла {event_file.name}: {str(e)}")
        else:
            logger.warning(f"Директория с данными о событиях не найдена: {events_dir}")
    
    return output_dir

def create_archive(output_dir, archive_path=None):
    """Создание архива с экспортированными данными"""
    logger = logging.getLogger('ExportLogs')
    
    output_dir = Path(output_dir)
    
    if not archive_path:
        archive_path = Path(f"windows_logs_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
    else:
        archive_path = Path(archive_path)
    
    logger.info(f"Создание архива: {archive_path}")
    
    try:
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(output_dir)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Архив успешно создан: {archive_path}")
        return archive_path
    except Exception as e:
        logger.error(f"Ошибка при создании архива: {str(e)}")
        return None

def get_agent_paths():
    """Определение путей к логам и данным агента"""
    logger = logging.getLogger('ExportLogs')
    
    # Пути по умолчанию
    service_data_path = Path("C:/ProgramData/WindowsMonitor")
    project_logs_path = project_root / "logs"
    
    agent_log_dir = None
    agent_data_dir = None
    
    # Ищем директорию с логами агента
    if project_logs_path.exists():
        agent_log_dir = project_logs_path
        logger.info(f"Найдена директория с логами агента: {agent_log_dir}")
    
    # Ищем директорию с данными агента в стандартных местах
    if service_data_path.exists() and (service_data_path / "data").exists():
        agent_data_dir = service_data_path
        logger.info(f"Найдена директория с данными агента: {agent_data_dir}")
    else:
        # Пробуем найти в проекте
        project_data_path = project_root / "data"
        if project_data_path.exists():
            agent_data_dir = project_root
            logger.info(f"Найдена директория с данными агента: {agent_data_dir}")
    
    # Проверяем конфигурацию, если доступна
    if agent_module_available:
        # Загружаем переменные окружения
        find_and_load_env()
        
        # Пытаемся найти и загрузить конфигурацию
        config_path = find_config_file()
        if config_path:
            try:
                config = load_config(config_path)
                
                # Проверяем наличие путей в конфигурации
                if 'log_dir' in config:
                    log_dir = Path(config['log_dir'])
                    if log_dir.exists():
                        agent_log_dir = log_dir
                        logger.info(f"Из конфигурации определена директория с логами: {agent_log_dir}")
                
                if 'data_dir' in config:
                    data_dir = Path(config['data_dir'])
                    if data_dir.exists():
                        agent_data_dir = data_dir
                        logger.info(f"Из конфигурации определена директория с данными: {agent_data_dir}")
            except Exception as e:
                logger.warning(f"Ошибка при загрузке конфигурации: {e}")
    
    return agent_log_dir, agent_data_dir

def main():
    parser = argparse.ArgumentParser(description='Экспорт логов Windows Monitor Agent')
    parser.add_argument('--days', type=int, default=7, help='Количество дней для экспорта')
    parser.add_argument('--output', default=None, help='Каталог для сохранения логов')
    parser.add_argument('--no-archive', action='store_true', help='Не создавать архив')
    parser.add_argument('--agent-logs', default=None, help='Путь к логам агента')
    parser.add_argument('--agent-data', default=None, help='Путь к данным агента')
    args = parser.parse_args()
    
    logger = setup_logging()
    logger.info(f"Начало экспорта логов за последние {args.days} дней")
    
    # Определяем каталог для выходных данных
    if args.output:
        output_dir = Path(args.output)
    else:
        date_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f"logs_export_{date_str}")
    
    # Получаем пути к логам и данным агента
    agent_log_dir, agent_data_dir = args.agent_logs, args.agent_data
    
    # Если пути не указаны, пытаемся определить их автоматически
    if not agent_log_dir or not agent_data_dir:
        auto_log_dir, auto_data_dir = get_agent_paths()
        
        if not agent_log_dir:
            agent_log_dir = auto_log_dir
        
        if not agent_data_dir:
            agent_data_dir = auto_data_dir
    
    logger.info(f"Экспорт в каталог: {output_dir}")
    
    # Экспорт логов Windows
    export_windows_events(output_dir, days=args.days)
    
    # Экспорт логов и данных агента
    export_agent_logs(output_dir, agent_log_dir, agent_data_dir)
    
    # Создание архива
    if not args.no_archive:
        archive_path = create_archive(output_dir)
        logger.info(f"Создан архив: {archive_path}")
        
        logger.info("Экспорт логов завершен")
        logger.info(f"Результаты доступны в архиве: {archive_path}")
    else:
        logger.info("Экспорт логов завершен")
        logger.info(f"Результаты доступны в каталоге: {output_dir}")

if __name__ == "__main__":
    main() 