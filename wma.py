#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import subprocess
import logging
import shutil
import platform
from pathlib import Path

# Добавляем директорию проекта в путь для импорта
script_path = Path(__file__).resolve()
project_root = script_path.parent
sys.path.append(str(project_root))

# Импорт функций из модуля src.agent
try:
    from src.agent import find_and_load_env, find_config_file, load_config, check_required_env_vars
except ImportError:
    pass  # Будет обработано далее

# Настройка логирования
def setup_logging():
    logger = logging.getLogger('WMA_Manager')
    logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# Получение директорий проекта
def get_project_dirs():
    script_path = Path(__file__).resolve()
    project_root = script_path.parent
    src_dir = project_root / 'src'
    scripts_dir = project_root / 'scripts'
    
    return project_root, src_dir, scripts_dir

# Проверка доступности модуля src.agent
def check_agent_module():
    try:
        from src.agent import find_and_load_env
        return True
    except ImportError:
        return False

# Проверка прав администратора
def is_admin():
    if platform.system() == 'Windows':
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    else:
        return os.geteuid() == 0  # Для Linux/Unix

# Запуск команды
def run_command(cmd, as_admin=False, shell=False):
    logger.info(f"Выполнение команды: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    if as_admin and platform.system() == 'Windows' and not is_admin():
        # Перезапуск с правами администратора
        import ctypes
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        return None
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=shell)
        if result.returncode != 0:
            logger.error(f"Ошибка выполнения команды: {result.stderr}")
            return None
        return result
    except Exception as e:
        logger.error(f"Исключение при выполнении команды: {str(e)}")
        return None

# Создание файла .env
def setup_env(force=False):
    project_root, _, _ = get_project_dirs()
    
    env_path = project_root / '.env'
    example_path = project_root / 'dotenv.example'
    
    if env_path.exists() and not force:
        logger.info(f"Файл .env уже существует в {env_path}")
        return
    
    if not example_path.exists():
        logger.error(f"Файл-пример dotenv.example не найден в {example_path}")
        return
    
    try:
        shutil.copy(example_path, env_path)
        logger.info(f"Создан файл .env в {env_path}")
        logger.info("Отредактируйте файл .env и добавьте ваши данные доступа к Telegram API")
        
        # Загружаем созданный .env файл
        if check_agent_module():
            find_and_load_env()
        
    except Exception as e:
        logger.error(f"Ошибка при создании файла .env: {str(e)}")

# Установка Sysmon
def install_sysmon():
    project_root, _, scripts_dir = get_project_dirs()
    
    if platform.system() != 'Windows':
        logger.error("Установка Sysmon доступна только в Windows")
        return
    
    if not is_admin():
        logger.warning("Для установки Sysmon требуются права администратора")
        logger.info("Перезапуск с правами администратора...")
        return run_command([sys.executable, __file__, "sysmon"], as_admin=True)
    
    # Проверяем наличие WSL и запускаем через bash, если есть
    wsl_exists = run_command(["where", "wsl"], shell=True)
    
    if wsl_exists:
        bash_script = scripts_dir / 'setup_sysmon.sh'
        if bash_script.exists():
            logger.info("Установка Sysmon через WSL/Bash...")
            run_command(["wsl", "bash", str(bash_script)], shell=True)
        else:
            logger.error(f"Скрипт {bash_script} не найден")
    else:
        # Запуск Python-скрипта установки Sysmon
        sysmon_script = scripts_dir / 'install_service.py'
        if sysmon_script.exists():
            logger.info("Установка Sysmon через Python...")
            run_command([sys.executable, str(sysmon_script), "--sysmon"], shell=True)
        else:
            logger.error(f"Скрипт {sysmon_script} не найден")

# Установка службы Windows
def install_service():
    _, _, scripts_dir = get_project_dirs()
    
    if platform.system() != 'Windows':
        logger.error("Установка службы доступна только в Windows")
        return
    
    if not is_admin():
        logger.warning("Для установки службы требуются права администратора")
        logger.info("Перезапуск с правами администратора...")
        return run_command([sys.executable, __file__, "install"], as_admin=True)
    
    # Загружаем переменные окружения перед установкой службы
    if check_agent_module():
        env_path = find_and_load_env()
        if env_path:
            logger.info(f"Загружены переменные окружения из {env_path}")
    
    service_script = scripts_dir / 'install_service.py'
    if service_script.exists():
        logger.info("Установка службы Windows Monitor Agent...")
        run_command([sys.executable, str(service_script), "--install"], shell=True)
    else:
        logger.error(f"Скрипт {service_script} не найден")

# Удаление службы Windows
def uninstall_service():
    _, _, scripts_dir = get_project_dirs()
    
    if platform.system() != 'Windows':
        logger.error("Удаление службы доступно только в Windows")
        return
    
    if not is_admin():
        logger.warning("Для удаления службы требуются права администратора")
        logger.info("Перезапуск с правами администратора...")
        return run_command([sys.executable, __file__, "uninstall"], as_admin=True)
    
    service_script = scripts_dir / 'install_service.py'
    if service_script.exists():
        logger.info("Удаление службы Windows Monitor Agent...")
        run_command([sys.executable, str(service_script), "--uninstall"], shell=True)
    else:
        logger.error(f"Скрипт {service_script} не найден")

# Запуск диагностики
def run_diagnostics():
    _, _, scripts_dir = get_project_dirs()
    
    diag_script = scripts_dir / 'diagnose.py'
    if diag_script.exists():
        logger.info("Запуск диагностики...")
        
        # Загружаем .env файл перед запуском диагностики
        if check_agent_module():
            env_path = find_and_load_env()
            if env_path:
                logger.info(f"Загружены переменные окружения из {env_path}")
        
        run_command([sys.executable, str(diag_script)], shell=True)
    else:
        logger.error(f"Скрипт {diag_script} не найден")

# Экспорт логов
def export_logs(days=7, output_dir=None):
    project_root, _, scripts_dir = get_project_dirs()
    
    export_script = scripts_dir / 'export_logs.py'
    if export_script.exists():
        cmd = [sys.executable, str(export_script), "--days", str(days)]
        
        if output_dir:
            cmd.extend(["--output", output_dir])
        
        # Загружаем .env файл перед экспортом логов
        if check_agent_module():
            env_path = find_and_load_env()
            if env_path:
                logger.info(f"Загружены переменные окружения из {env_path}")
        
        logger.info(f"Экспорт логов за последние {days} дней...")
        run_command(cmd, shell=True)
    else:
        logger.error(f"Скрипт {export_script} не найден")

# Запуск агента вручную
def run_agent():
    project_root, src_dir, _ = get_project_dirs()
    
    main_script = src_dir / 'agent' / 'main.py'
    if main_script.exists():
        logger.info("Запуск агента мониторинга...")
        
        # Создаем директорию для логов, если она не существует
        log_dir = project_root / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        # Загружаем переменные окружения и конфигурацию
        config_path = None
        if check_agent_module():
            env_path = find_and_load_env()
            if env_path:
                logger.info(f"Загружены переменные окружения из {env_path}")
            
            config_path = find_config_file()
            if config_path:
                logger.info(f"Найден файл конфигурации: {config_path}")
                
                # Проверяем наличие всех необходимых переменных
                try:
                    config = load_config(config_path)
                    missing_vars = check_required_env_vars(config)
                    if missing_vars:
                        logger.warning(f"Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
                        logger.warning("Обновите файл .env или config.json перед запуском агента")
                except Exception as e:
                    logger.error(f"Ошибка при загрузке конфигурации: {e}")
        
        if not config_path:
            config_path = project_root / 'config.json'
        
        # Запускаем агента
        cmd = [sys.executable, str(main_script), "--config", str(config_path), "--log-dir", str(log_dir)]
        try:
            subprocess.Popen(cmd)
            logger.info("Агент запущен в фоновом режиме")
        except Exception as e:
            logger.error(f"Ошибка при запуске агента: {str(e)}")
    else:
        logger.error(f"Скрипт {main_script} не найден")

# Установка и настройка всех компонентов
def setup_all():
    logger.info("Начало полной настройки системы...")
    
    # 1. Создание .env файла
    setup_env()
    
    # 2. Установка Sysmon (если Windows)
    if platform.system() == 'Windows':
        if not is_admin():
            logger.warning("Некоторые шаги требуют прав администратора")
            logger.info("Запустите скрипт повторно с правами администратора для полной настройки")
        else:
            install_sysmon()
            install_service()
    
    # 3. Запуск диагностики
    run_diagnostics()
    
    logger.info("Настройка завершена!")
    logger.info("Не забудьте отредактировать файл .env и добавить ваши данные доступа к Telegram API")

# Основная функция
def main():
    parser = argparse.ArgumentParser(description='Windows Monitor Agent - управление и настройка')
    
    # Подкоманды
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда setup - создает .env файл
    setup_parser = subparsers.add_parser('setup', help='Создание файла .env')
    setup_parser.add_argument('--force', action='store_true', help='Пересоздать файл, если он уже существует')
    
    # Команда sysmon - устанавливает Sysmon
    subparsers.add_parser('sysmon', help='Установка Sysmon')
    
    # Команда install - устанавливает службу
    subparsers.add_parser('install', help='Установка службы Windows Monitor Agent')
    
    # Команда uninstall - удаляет службу
    subparsers.add_parser('uninstall', help='Удаление службы Windows Monitor Agent')
    
    # Команда diagnose - запускает диагностику
    subparsers.add_parser('diagnose', help='Запуск диагностики системы')
    
    # Команда export - экспортирует логи
    export_parser = subparsers.add_parser('export', help='Экспорт логов')
    export_parser.add_argument('--days', type=int, default=7, help='Количество дней для экспорта (по умолчанию: 7)')
    export_parser.add_argument('--output', help='Директория для сохранения логов')
    
    # Команда run - запускает агента вручную
    subparsers.add_parser('run', help='Запуск агента вручную')
    
    # Команда all - полная настройка
    subparsers.add_parser('all', help='Полная настройка системы')
    
    args = parser.parse_args()
    
    # Если команда не указана, показываем справку
    if not args.command:
        parser.print_help()
        return
    
    # Выполнение выбранной команды
    if args.command == 'setup':
        setup_env(args.force)
    elif args.command == 'sysmon':
        install_sysmon()
    elif args.command == 'install':
        install_service()
    elif args.command == 'uninstall':
        uninstall_service()
    elif args.command == 'diagnose':
        run_diagnostics()
    elif args.command == 'export':
        export_logs(args.days, args.output)
    elif args.command == 'run':
        run_agent()
    elif args.command == 'all':
        setup_all()

if __name__ == '__main__':
    main() 