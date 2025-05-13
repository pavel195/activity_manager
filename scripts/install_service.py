import os
import sys
import argparse
import subprocess
import winreg
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import logging
from pathlib import Path

# Добавляем директорию проекта в путь для импорта
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
SRC_DIR = ROOT_DIR / 'src'
sys.path.append(str(ROOT_DIR))

# Импорт функций из модуля src.agent
agent_module_available = False
try:
    from src.agent import find_and_load_env, find_config_file, load_config
    agent_module_available = True
except ImportError:
    pass  # Будет обработано далее

class WindowsMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "WindowsMonitorAgent"
    _svc_display_name_ = "Windows Monitor Agent"
    _svc_description_ = "Мониторинг активности на Windows ПК и отправка уведомлений в Telegram"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.logger = self._setup_logging()
        socket.setdefaulttimeout(60)
        
    def _setup_logging(self):
        logger = logging.getLogger('WindowsMonitorService')
        logger.setLevel(logging.INFO)
        
        log_dir = Path('C:/ProgramData/WindowsMonitor/logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / 'service.log'
        handler = logging.FileHandler(log_file)
        
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def SvcStop(self):
        self.logger.info("Service stop signal received")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        
        # Останавливаем процесс агента
        try:
            subprocess.call(['taskkill', '/F', '/IM', 'python.exe'], stderr=subprocess.PIPE)
        except Exception as e:
            self.logger.error(f"Error stopping agent process: {str(e)}")
    
    def SvcDoRun(self):
        self.logger.info("Service starting")
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                             servicemanager.PYS_SERVICE_STARTED,
                             (self._svc_name_, ''))
        self.main()
    
    def main(self):
        # Директория для конфигурации
        config_dir = Path('C:/ProgramData/WindowsMonitor')
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Пути к файлам
        python_exe = sys.executable
        script_path = SRC_DIR / 'agent' / 'main.py'
        config_path = config_dir / 'config.json'
        env_path = config_dir / '.env'
        log_dir = config_dir / 'logs'
        
        # Если доступен модуль агента, пытаемся использовать его для поиска конфигурации
        if agent_module_available:
            # Загружаем переменные окружения
            found_env_path = find_and_load_env()
            if found_env_path:
                self.logger.info(f"Загружены переменные окружения из {found_env_path}")
            
            # Если конфиг не существует, пытаемся найти его
            if not config_path.exists():
                found_config_path = find_config_file()
                if found_config_path:
                    import shutil
                    shutil.copy(found_config_path, config_path)
                    self.logger.info(f"Скопирован конфигурационный файл из {found_config_path} в {config_path}")
        
        # Проверяем существование конфиг-файла, если нет - копируем дефолтный
        if not config_path.exists():
            default_config = ROOT_DIR / 'config.json'
            if default_config.exists():
                import shutil
                shutil.copy(default_config, config_path)
                self.logger.info(f"Copied default config to {config_path}")
            else:
                self.logger.error(f"Default config not found at {default_config}")
                return
        
        # Проверяем существование .env файла, если нет - проверяем в корне проекта
        if not env_path.exists():
            default_env = ROOT_DIR / '.env'
            dotenv_example = ROOT_DIR / 'dotenv.example'
            
            if default_env.exists():
                import shutil
                shutil.copy(default_env, env_path)
                self.logger.info(f"Copied .env file to {env_path}")
            elif dotenv_example.exists():
                import shutil
                shutil.copy(dotenv_example, env_path)
                self.logger.info(f"Copied dotenv.example to {env_path}")
                self.logger.warning("You should edit the .env file and add your credentials")
        
        # Запускаем агента
        try:
            self.logger.info(f"Starting agent with config {config_path}")
            
            cmd = [
                python_exe, 
                str(script_path),
                '--config', str(config_path),
                '--log-dir', str(log_dir)
            ]
            
            self.logger.info(f"Command: {' '.join(cmd)}")
            process = subprocess.Popen(cmd)
            
            # Ждем сигнала остановки или завершения процесса
            while True:
                rc = win32event.WaitForSingleObject(self.stop_event, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    # Получен сигнал остановки
                    break
                
                # Проверяем не упал ли процесс
                if process.poll() is not None:
                    self.logger.error(f"Agent process terminated with code {process.returncode}")
                    # Перезапускаем процесс
                    process = subprocess.Popen(cmd)
            
            self.logger.info("Service stopping")
        except Exception as e:
            self.logger.error(f"Error in service main loop: {str(e)}")

def install_service():
    try:
        print("Установка службы Windows Monitor Agent...")
        
        # Устанавливаем службу
        subprocess.call([sys.executable, __file__, '--startup', 'auto', 'install'])
        
        print("Служба успешно установлена!")
        print("Запуск службы...")
        
        # Запускаем службу
        subprocess.call(['net', 'start', 'WindowsMonitorAgent'])
        
        print("Служба запущена и настроена на автозапуск.")
        return True
    except Exception as e:
        print(f"Ошибка при установке службы: {str(e)}")
        return False

def uninstall_service():
    try:
        print("Остановка службы Windows Monitor Agent...")
        
        # Останавливаем службу
        try:
            subprocess.call(['net', 'stop', 'WindowsMonitorAgent'])
        except:
            pass
        
        print("Удаление службы...")
        
        # Удаляем службу
        subprocess.call([sys.executable, __file__, 'remove'])
        
        print("Служба успешно удалена.")
        return True
    except Exception as e:
        print(f"Ошибка при удалении службы: {str(e)}")
        return False

def check_admin():
    try:
        # Попытка открыть защищенный раздел реестра требует админ-прав
        winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Windows", 0, winreg.KEY_WRITE)
        return True
    except:
        return False

def install_sysmon():
    try:
        print("Установка и настройка Sysmon...")
        
        sysmon_dir = Path('C:/ProgramData/WindowsMonitor/tools')
        sysmon_dir.mkdir(parents=True, exist_ok=True)
        
        # Пути к файлам
        sysmon_exe = sysmon_dir / 'Sysmon.exe'
        sysmon_config = ROOT_DIR / 'sysmon_config.xml'
        
        # Проверяем существование Sysmon
        if not sysmon_exe.exists():
            print("Sysmon не найден. Пожалуйста, скачайте Sysmon со страницы Microsoft Sysinternals")
            print("и скопируйте его в C:/ProgramData/WindowsMonitor/tools/")
            return False
        
        # Проверяем существование конфига
        if not sysmon_config.exists():
            print(f"Конфигурация Sysmon не найдена по пути {sysmon_config}")
            return False
        
        # Устанавливаем Sysmon
        print("Запуск установки Sysmon...")
        result = subprocess.call([
            str(sysmon_exe),
            '-i',
            str(sysmon_config),
            '-accepteula'
        ])
        
        if result == 0:
            print("Sysmon успешно установлен и настроен.")
            return True
        else:
            print(f"Ошибка при установке Sysmon (код {result}).")
            return False
    except Exception as e:
        print(f"Ошибка при установке Sysmon: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Установка и управление службой Windows Monitor Agent')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--install', action='store_true', help='Установить службу')
    group.add_argument('--uninstall', action='store_true', help='Удалить службу')
    group.add_argument('--sysmon', action='store_true', help='Установить и настроить Sysmon')
    
    # Параметры для обработки PythonService
    if len(sys.argv) > 1 and sys.argv[1] != '--install' and sys.argv[1] != '--uninstall' and sys.argv[1] != '--sysmon':
        win32serviceutil.HandleCommandLine(WindowsMonitorService)
        return
    
    args = parser.parse_args()
    
    # Проверяем наличие админ-прав
    if not check_admin():
        print("Для выполнения этих операций требуются права администратора.")
        print("Пожалуйста, запустите скрипт с правами администратора.")
        return
    
    if args.install:
        # Если доступен модуль агента, загружаем переменные окружения
        if agent_module_available:
            env_path = find_and_load_env()
            if env_path:
                print(f"Загружены переменные окружения из {env_path}")
                
        if install_service():
            print("Служба успешно установлена и запущена.")
    elif args.uninstall:
        if uninstall_service():
            print("Служба успешно удалена.")
    elif args.sysmon:
        if install_sysmon():
            print("Sysmon успешно установлен и настроен.")

if __name__ == '__main__':
    main() 