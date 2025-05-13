import os
import sys
import json
import time
import logging
import argparse
import threading
import signal
from pathlib import Path
from dotenv import load_dotenv

from . import find_and_load_env, find_config_file, load_config, check_required_env_vars
from event_monitor import EventMonitor
from event_handler import EventHandler
from telegram_notifier import TelegramNotifier
import schedule

# Настройка логгирования
def setup_logging(log_dir):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / 'agent.log'
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Обработчик для вывода в файл
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
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

# Отправка ежедневного отчета
def send_daily_report(event_handler, telegram_notifier):
    logger = logging.getLogger('DailyReport')
    try:
        logger.info("Generating daily report")
        report = event_handler.get_daily_report()
        
        if 'status' in report:
            logger.warning(f"Failed to generate report: {report['status']}")
            telegram_notifier.send_message(f"❌ Ошибка формирования ежедневного отчета: {report['status']}")
            return
        
        # Сохраняем отчет в формате PDF
        from fpdf import FPDF
        import tempfile
        
        date_str = report['date']
        
        # Создаем PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Заголовок
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f"Ежедневный отчет за {date_str}", 0, 1, 'C')
        pdf.ln(10)
        
        # Сводка
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, "Сводка:", 0, 1)
        
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 8, f"Запусков системы: {report['startup_count']}", 0, 1)
        pdf.cell(0, 8, f"Входов в систему: {report['login_count']}", 0, 1)
        pdf.cell(0, 8, f"Повышений привилегий: {report['privilege_count']}", 0, 1)
        pdf.cell(0, 8, f"Изменений задач: {report['task_count']}", 0, 1)
        pdf.cell(0, 8, f"Изменений служб: {report['service_count']}", 0, 1)
        pdf.cell(0, 8, f"Подозрительных процессов: {report['suspicious_process_count']}", 0, 1)
        
        # Сохраняем PDF
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        pdf_path = temp_file.name
        pdf.output(pdf_path)
        
        # Отправляем отчет в Telegram
        telegram_notifier.send_document(pdf_path, f"Ежедневный отчет за {date_str}")
        
        # Удаляем временный файл
        os.unlink(pdf_path)
        
        logger.info("Daily report sent successfully")
    except Exception as e:
        logger.error(f"Error sending daily report: {str(e)}")
        telegram_notifier.send_message(f"❌ Ошибка отправки ежедневного отчета: {str(e)}")

# Основной класс агента
class WindowsMonitorAgent:
    def __init__(self, config):
        if isinstance(config, (str, Path)):
            # Если передан путь к файлу конфигурации
            self.config_path = Path(config)
            self.config = load_config(self.config_path)
        else:
            # Если передана уже загруженная конфигурация
            self.config_path = None
            self.config = config
            
        self.logger = logging.getLogger('Agent')
        self.stop_event = threading.Event()
        
        # Создаем компоненты
        self.telegram = TelegramNotifier(self.config)
        self.event_handler = EventHandler(self.config, self.telegram)
        self.event_monitor = EventMonitor(self.config, self.event_handler)
        
        # Устанавливаем ссылку на обработчик событий в Telegram-клиенте
        self.telegram.event_handler = self.event_handler
        
        # Настраиваем планировщик для ежедневного отчета
        if self.config['features'].get('daily_report', True):
            report_time = self.config.get('reporting', {}).get('report_time', '20:00')
            schedule.every().day.at(report_time).do(
                send_daily_report, self.event_handler, self.telegram
            )
    
    def start(self):
        self.logger.info("Starting Windows Monitor Agent")
        
        # Запускаем компоненты
        self.telegram.start()
        self.event_monitor.start()
        
        # Отправляем уведомление о запуске
        hostname = os.environ.get('COMPUTERNAME', 'Unknown')
        self.telegram.send_message(f"🚀 Агент мониторинга запущен\nХост: {hostname}\nВремя: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Запускаем основной цикл
        self._run_loop()
    
    def stop(self):
        self.logger.info("Stopping Windows Monitor Agent")
        self.stop_event.set()
        
        # Останавливаем компоненты
        self.event_monitor.stop()
        self.telegram.stop()
        
        self.logger.info("Agent stopped")
    
    def _run_loop(self):
        self.logger.info("Agent main loop started")
        
        try:
            while not self.stop_event.is_set():
                # Запускаем задачи планировщика
                schedule.run_pending()
                
                # Периодическая проверка конфигурации
                # TODO: Добавить перезагрузку конфигурации при изменении файла
                
                # Спим чтобы не грузить процессор
                time.sleep(1)
        except Exception as e:
            self.logger.error(f"Error in main loop: {str(e)}")
        
        self.logger.info("Agent main loop stopped")

# Обработчик сигналов для корректного завершения
def signal_handler(sig, frame, agent):
    logging.info(f"Received signal {sig}, shutting down...")
    agent.stop()
    sys.exit(0)

# Точка входа
def main():
    parser = argparse.ArgumentParser(description='Windows Monitor Agent')
    parser.add_argument('--config', default='config.json', help='Path to config file')
    parser.add_argument('--log-dir', default='./logs', help='Path to log directory')
    args = parser.parse_args()
    
    # Настраиваем логирование
    logger = setup_logging(args.log_dir)
    
    try:
        # Загружаем переменные окружения
        env_path = find_and_load_env()
        if env_path:
            logger.info(f"Загружены переменные окружения из файла {env_path}")
        else:
            logger.warning("Файл .env не найден, используется только конфигурационный файл")
        
        # Пытаемся найти конфигурационный файл, если указанный не существует
        config_path = Path(args.config)
        if not config_path.exists():
            config_path = find_config_file()
            
        if not config_path:
            logger.error(f"Конфигурационный файл не найден: {args.config}")
            sys.exit(1)
        
        logger.info(f"Используется конфигурационный файл: {config_path}")
        config = load_config(config_path)
        
        # Проверяем обязательные переменные окружения
        missing_vars = check_required_env_vars(config)
        if missing_vars:
            logger.error(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
            logger.error("Создайте файл .env или укажите эти переменные в конфигурационном файле")
            sys.exit(1)
        
        # Создаем и запускаем агента
        agent = WindowsMonitorAgent(config)
        
        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, agent))
        signal.signal(signal.SIGTERM, lambda sig, frame: signal_handler(sig, frame, agent))
        
        # Запускаем агента
        agent.start()
    except Exception as e:
        logger.error(f"Ошибка запуска агента: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 