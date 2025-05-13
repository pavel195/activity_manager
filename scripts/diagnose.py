#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import platform
import logging
import subprocess
import socket
import json
from pathlib import Path

# Добавляем директорию проекта в путь для импорта
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent
sys.path.append(str(project_root))

# Импорт функций из модуля src.agent
agent_module_available = False
try:
    from src.agent import find_and_load_env, find_config_file, load_config, check_required_env_vars
    agent_module_available = True
except ImportError:
    from dotenv import load_dotenv

def setup_logging():
    logger = logging.getLogger('Diagnostics')
    logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger

def check_environment():
    """Проверка системного окружения"""
    logger = logging.getLogger('Diagnostics')
    
    logger.info(f"Операционная система: {platform.system()} {platform.release()} ({platform.version()})")
    logger.info(f"Архитектура: {platform.machine()}")
    logger.info(f"Имя компьютера: {platform.node()}")
    logger.info(f"Python версия: {platform.python_version()}")
    logger.info(f"Путь к Python: {sys.executable}")
    logger.info("")
    
    return True

def check_dotenv():
    """Проверка наличия .env файла и его содержимого"""
    logger = logging.getLogger('Diagnostics')
    
    # Проверяем в различных местах по тому же алгоритму, что и в основном агенте
    if agent_module_available:
        env_path = find_and_load_env()
        if env_path:
            logger.info(f"Найден .env файл: {env_path}")
            env_found = True
        else:
            env_found = False
    else:
        env_paths = [
            Path(".env"),  # Текущая директория
            Path(__file__).resolve().parent.parent / ".env",  # Корневая директория проекта
            Path("C:/ProgramData/WindowsMonitor/.env"),  # Директория установки службы
            Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / "WindowsMonitor/.env"  # С использованием переменной окружения
        ]
        
        env_found = False
        
        for env_path in env_paths:
            if env_path.exists():
                logger.info(f"Найден .env файл: {env_path}")
                env_found = True
                
                # Загружаем переменные и проверяем наличие необходимых
                load_dotenv(dotenv_path=env_path)
                break
            
    # Проверяем необходимые переменные
    telegram_token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if telegram_token:
        logger.info("✅ TELEGRAM_TOKEN найден")
        
        # Проверяем валидность токена (первые символы)
        if len(telegram_token) > 10 and ":" in telegram_token:
            logger.info("✅ TELEGRAM_TOKEN имеет правильный формат")
        else:
            logger.warning("❌ TELEGRAM_TOKEN имеет неправильный формат. Должен содержать символ ':'")
    else:
        logger.warning("❌ TELEGRAM_TOKEN не найден")
    
    if chat_id:
        logger.info("✅ CHAT_ID найден")
    else:
        logger.warning("❌ CHAT_ID не найден")
    
    # Проверяем опциональные переменные
    vt_api_key = os.environ.get('VT_API_KEY')
    if vt_api_key:
        logger.info("✅ VT_API_KEY найден")
    else:
        logger.info("ℹ️ VT_API_KEY не найден (опционально)")
    
    if not env_found:
        logger.warning("❌ .env файл не найден")
        logger.info("ℹ️ Проверьте наличие .env файла в следующих местах:")
        if agent_module_available:
            env_paths = [
                Path(".env"),  # Текущая директория
                Path(__file__).resolve().parent.parent / ".env",  # Корневая директория проекта
                Path("C:/ProgramData/WindowsMonitor/.env"),  # Директория установки службы
                Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / "WindowsMonitor/.env"  # С использованием переменной окружения
            ]
        for path in env_paths:
            logger.info(f"   - {path}")
    
    logger.info("")
    return env_found

def check_config():
    """Проверка конфигурационного файла"""
    logger = logging.getLogger('Diagnostics')
    
    if agent_module_available:
        config_path = find_config_file()
        if config_path:
            logger.info(f"Найден config.json: {config_path}")
            config_found = True
            
            try:
                config = load_config(config_path)
                missing_vars = check_required_env_vars(config)
                
                # Проверяем основные настройки с учетом возможности наличия в .env
                if missing_vars:
                    logger.warning(f"❌ Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
                else:
                    logger.info("✅ Все обязательные переменные найдены (в config.json или .env)")
                
                # Проверяем наличие разделов конфигурации
                if 'features' in config:
                    logger.info("✅ Секция features найдена в config.json")
                    # Проверяем содержимое секции features
                    features = config.get('features', {})
                    if isinstance(features, dict):
                        logger.info("  - track_processes: " + ("✅" if features.get('track_processes', True) else "❌"))
                        logger.info("  - track_services: " + ("✅" if features.get('track_services', True) else "❌"))
                        logger.info("  - track_logins: " + ("✅" if features.get('track_logins', True) else "❌"))
                        logger.info("  - daily_report: " + ("✅" if features.get('daily_report', True) else "❌"))
                    else:
                        logger.warning("❌ Секция features имеет неверный формат")
                else:
                    logger.warning("❌ Секция features не найдена в config.json")
                
                if 'monitoring' in config:
                    logger.info("✅ Секция monitoring найдена в config.json")
                    # Проверка списков мониторинга
                    monitoring = config.get('monitoring', {})
                    if isinstance(monitoring, dict):
                        logger.info(f"  - process_whitelist: {len(monitoring.get('process_whitelist', []))} элементов")
                        logger.info(f"  - service_whitelist: {len(monitoring.get('service_whitelist', []))} элементов")
                        logger.info(f"  - task_whitelist: {len(monitoring.get('task_whitelist', []))} элементов")
                    else:
                        logger.warning("❌ Секция monitoring имеет неверный формат")
                else:
                    logger.warning("❌ Секция monitoring не найдена в config.json")
                
                if 'reporting' in config:
                    logger.info("✅ Секция reporting найдена в config.json")
                    # Проверка настроек отчетов
                    reporting = config.get('reporting', {})
                    if isinstance(reporting, dict):
                        logger.info(f"  - report_time: {reporting.get('report_time', '20:00')}")
                        logger.info(f"  - report_format: {reporting.get('report_format', 'markdown')}")
                    else:
                        logger.warning("❌ Секция reporting имеет неверный формат")
                else:
                    logger.warning("❌ Секция reporting не найдена в config.json")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при чтении config.json: {str(e)}")
        else:
            config_found = False
    else:
        # Используем старый код, если модуль недоступен
        # Возможные пути к конфигам
        config_paths = [
            Path("config.json"),
            Path(__file__).resolve().parent.parent / "config.json",
            Path("C:/ProgramData/WindowsMonitor/config.json"),
            Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / "WindowsMonitor/config.json"
        ]
        
        config_found = False
        env_loaded = os.environ.get('TELEGRAM_TOKEN') is not None
        
        for config_path in config_paths:
            if config_path.exists():
                logger.info(f"Найден config.json: {config_path}")
                config_found = True
                
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    # Проверяем основные настройки с учетом возможности наличия в .env
                    if 'telegram_token' in config and config['telegram_token']:
                        logger.info("✅ telegram_token найден в config.json")
                    elif env_loaded:
                        logger.info("✅ telegram_token найден в .env файле")
                    else:
                        logger.warning("❌ telegram_token не найден в config.json или .env")
                    
                    if 'chat_id' in config and config['chat_id']:
                        logger.info("✅ chat_id найден в config.json")
                    elif os.environ.get('CHAT_ID'):
                        logger.info("✅ chat_id найден в .env файле")
                    else:
                        logger.warning("❌ chat_id не найден в config.json или .env")
                    
                    # Проверяем наличие разделов конфигурации
                    if 'features' in config:
                        logger.info("✅ Секция features найдена в config.json")
                        # Проверяем содержимое секции features
                        features = config.get('features', {})
                        if isinstance(features, dict):
                            logger.info("  - track_processes: " + ("✅" if features.get('track_processes', True) else "❌"))
                            logger.info("  - track_services: " + ("✅" if features.get('track_services', True) else "❌"))
                            logger.info("  - track_logins: " + ("✅" if features.get('track_logins', True) else "❌"))
                            logger.info("  - daily_report: " + ("✅" if features.get('daily_report', True) else "❌"))
                        else:
                            logger.warning("❌ Секция features имеет неверный формат")
                    else:
                        logger.warning("❌ Секция features не найдена в config.json")
                    
                    if 'monitoring' in config:
                        logger.info("✅ Секция monitoring найдена в config.json")
                        # Проверка списков мониторинга
                        monitoring = config.get('monitoring', {})
                        if isinstance(monitoring, dict):
                            logger.info(f"  - process_whitelist: {len(monitoring.get('process_whitelist', []))} элементов")
                            logger.info(f"  - service_whitelist: {len(monitoring.get('service_whitelist', []))} элементов")
                            logger.info(f"  - task_whitelist: {len(monitoring.get('task_whitelist', []))} элементов")
                        else:
                            logger.warning("❌ Секция monitoring имеет неверный формат")
                    else:
                        logger.warning("❌ Секция monitoring не найдена в config.json")
                    
                    if 'reporting' in config:
                        logger.info("✅ Секция reporting найдена в config.json")
                        # Проверка настроек отчетов
                        reporting = config.get('reporting', {})
                        if isinstance(reporting, dict):
                            logger.info(f"  - report_time: {reporting.get('report_time', '20:00')}")
                            logger.info(f"  - report_format: {reporting.get('report_format', 'markdown')}")
                        else:
                            logger.warning("❌ Секция reporting имеет неверный формат")
                    else:
                        logger.warning("❌ Секция reporting не найдена в config.json")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при чтении config.json: {str(e)}")
                
                break
    
    if not config_found:
        logger.warning("❌ config.json не найден")
        logger.info("ℹ️ Проверьте наличие config.json в следующих местах:")
        if agent_module_available:
            config_paths = [
                Path("config.json"),
                Path(__file__).resolve().parent.parent / "config.json",
                Path("C:/ProgramData/WindowsMonitor/config.json"),
                Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / "WindowsMonitor/config.json"
            ]
        for path in config_paths:
            logger.info(f"   - {path}")
    
    logger.info("")
    return config_found

def check_network():
    """Проверка сетевого соединения"""
    logger = logging.getLogger('Diagnostics')
    
    logger.info("Проверка сетевого соединения...")
    
    # Проверка доступности api.telegram.org
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        result = s.connect_ex(('api.telegram.org', 443))
        if result == 0:
            logger.info("✅ api.telegram.org доступен")
        else:
            logger.warning(f"❌ api.telegram.org недоступен (код ошибки: {result})")
        s.close()
    except Exception as e:
        logger.warning(f"❌ Ошибка при проверке доступности api.telegram.org: {str(e)}")
    
    # Проверка доступности VirusTotal API если настроен
    if os.environ.get('VT_API_KEY'):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            result = s.connect_ex(('www.virustotal.com', 443))
            if result == 0:
                logger.info("✅ www.virustotal.com доступен")
            else:
                logger.warning(f"❌ www.virustotal.com недоступен (код ошибки: {result})")
            s.close()
        except Exception as e:
            logger.warning(f"❌ Ошибка при проверке доступности www.virustotal.com: {str(e)}")
    
    logger.info("")
    return True

def check_dependencies():
    """Проверка зависимостей Python"""
    logger = logging.getLogger('Diagnostics')
    
    logger.info("Проверка зависимостей Python...")
    
    dependencies = [
        'pywin32',
        'python-telegram-bot',
        'pyyaml',
        'schedule',
        'requests',
        'pyclamd',
        'fpdf2',
        'psutil',
        'python-dotenv',
        'winreg-patcher'
    ]
    
    missing_deps = []
    
    try:
        for dep in dependencies:
            try:
                __import__(dep.replace('-', '_'))
                logger.info(f"✅ {dep} установлен")
            except ImportError:
                logger.warning(f"❌ {dep} не установлен")
                missing_deps.append(dep)
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке зависимостей: {str(e)}")
    
    if missing_deps:
        logger.warning("\nНеобходимо установить следующие зависимости:")
        logger.warning(f"pip install {' '.join(missing_deps)}")
    else:
        logger.info("✅ Все зависимости установлены")
    
    logger.info("")
    return len(missing_deps) == 0

def check_services():
    """Проверка состояния службы WindowsMonitorAgent и Sysmon"""
    logger = logging.getLogger('Diagnostics')
    
    logger.info("Проверка состояния служб...")
    
    try:
        # Проверяем службу WindowsMonitorAgent
        result = subprocess.run(['sc', 'query', 'WindowsMonitorAgent'], 
                                capture_output=True, text=True, encoding='cp866')
        
        if 'RUNNING' in result.stdout:
            logger.info("✅ Служба WindowsMonitorAgent запущена")
        elif 'STOPPED' in result.stdout:
            logger.warning("❌ Служба WindowsMonitorAgent остановлена")
        elif result.returncode == 1060:  # Код ошибки, когда служба не существует
            logger.warning("❌ Служба WindowsMonitorAgent не установлена")
        else:
            logger.warning(f"❌ Неизвестное состояние службы WindowsMonitorAgent: {result.stdout}")
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке службы WindowsMonitorAgent: {str(e)}")
    
    try:
        # Проверяем службу Sysmon
        result = subprocess.run(['sc', 'query', 'Sysmon'], 
                                capture_output=True, text=True, encoding='cp866')
        
        if 'RUNNING' in result.stdout:
            logger.info("✅ Служба Sysmon запущена")
        elif 'STOPPED' in result.stdout:
            logger.warning("❌ Служба Sysmon остановлена")
        elif result.returncode == 1060:  # Код ошибки, когда служба не существует
            logger.warning("❌ Служба Sysmon не установлена")
        else:
            logger.warning(f"❌ Неизвестное состояние службы Sysmon: {result.stdout}")
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке службы Sysmon: {str(e)}")
    
    logger.info("")
    return True

def main():
    parser = argparse.ArgumentParser(description='Диагностика Windows Monitor Agent')
    parser.add_argument('--verbose', '-v', action='store_true', help='Подробный вывод')
    args = parser.parse_args()
    
    logger = setup_logging()
    
    logger.info("=== Диагностика Windows Monitor Agent ===\n")
    
    # Проверяем окружение
    check_environment()
    
    # Проверяем .env файл
    check_dotenv()
    
    # Проверяем конфигурационный файл
    check_config()
    
    # Проверяем сетевое соединение
    check_network()
    
    # Проверяем зависимости
    check_dependencies()
    
    # Проверяем службы
    check_services()
    
    logger.info("=== Диагностика завершена ===")

if __name__ == "__main__":
    import argparse
    main() 