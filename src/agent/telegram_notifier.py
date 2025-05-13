import logging
import asyncio
import threading
import time
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from fpdf import FPDF
import datetime
import json
import tempfile

class TelegramNotifier:
    def __init__(self, config, event_handler=None):
        self.config = config
        self.token = config.get('telegram_token', '')
        self.chat_id = config.get('chat_id', '')
        self.event_handler = event_handler
        self.bot = None
        self.app = None
        self.message_queue = []
        self.queue_lock = threading.Lock()
        self.send_thread = None
        self.is_running = False
        
        self.setup_logging()
        
    def setup_logging(self):
        self.logger = logging.getLogger('TelegramNotifier')
        self.logger.setLevel(logging.INFO)
        
    def start(self):
        if not self.token or not self.chat_id:
            self.logger.error("Telegram token or chat_id not provided in config")
            return False
            
        try:
            self.bot = Bot(self.token)
            
            # Start message sending thread
            self.is_running = True
            self.send_thread = threading.Thread(target=self._message_sender_loop, daemon=True)
            self.send_thread.start()
            
            # Start bot application in another thread
            self.bot_thread = threading.Thread(target=self._run_bot, daemon=True)
            self.bot_thread.start()
            
            self.logger.info("Telegram notifier started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start Telegram notifier: {str(e)}")
            return False
    
    def stop(self):
        self.is_running = False
        
        if self.send_thread:
            self.send_thread.join(timeout=5.0)
            
        if self.app:
            asyncio.run_coroutine_threadsafe(self.app.stop(), self.app.loop)
            
        self.logger.info("Telegram notifier stopped")
        return True
    
    def send_message(self, message):
        if not message:
            return False
            
        with self.queue_lock:
            self.message_queue.append(('text', message))
            
        return True
    
    def send_document(self, document_path, caption=None):
        if not document_path:
            return False
            
        with self.queue_lock:
            self.message_queue.append(('document', (document_path, caption)))
            
        return True
    
    def _message_sender_loop(self):
        while self.is_running:
            messages_to_send = []
            
            # Get messages from queue
            with self.queue_lock:
                if self.message_queue:
                    messages_to_send = self.message_queue.copy()
                    self.message_queue.clear()
            
            # Send messages
            for msg_type, content in messages_to_send:
                try:
                    if msg_type == 'text':
                        asyncio.run(self._send_message_async(content))
                    elif msg_type == 'document':
                        doc_path, caption = content
                        asyncio.run(self._send_document_async(doc_path, caption))
                except Exception as e:
                    self.logger.error(f"Error sending message: {str(e)}")
                    # Put back in queue
                    with self.queue_lock:
                        self.message_queue.append((msg_type, content))
            
            # Sleep a bit to avoid too many API calls
            time.sleep(1)
    
    async def _send_message_async(self, message):
        if self.bot and self.chat_id:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='Markdown')
    
    async def _send_document_async(self, document_path, caption=None):
        if self.bot and self.chat_id:
            with open(document_path, 'rb') as document:
                await self.bot.send_document(chat_id=self.chat_id, document=document, caption=caption)
    
    def _run_bot(self):
        """Run the bot application in a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        self.app = Application.builder().token(self.token).build()
        
        # Register command handlers
        self.app.add_handler(CommandHandler("status", self._status_command))
        self.app.add_handler(CommandHandler("report", self._report_command))
        self.app.add_handler(CommandHandler("help", self._help_command))
        
        # Start the Bot
        loop.run_until_complete(self.app.initialize())
        loop.run_until_complete(self.app.start())
        loop.run_until_complete(self.app.updater.start_polling())
        
        try:
            loop.run_forever()
        except (KeyboardInterrupt, SystemExit):
            loop.run_until_complete(self.app.stop())
            loop.run_until_complete(self.app.updater.stop())
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /status command."""
        if not self.event_handler:
            await update.message.reply_text("Статус недоступен - обработчик событий не инициализирован")
            return
            
        status = self.event_handler.get_system_status()
        
        message = f"📊 *Статус системы*\n\n"
        message += f"🖥️ Хост: `{status['hostname']}`\n"
        message += f"⏱️ Аптайм: `{status['uptime']}` (с {status['uptime_since']})\n"
        message += f"🕒 Текущее время: `{status['current_time']}`\n\n"
        
        if status['latest_events']:
            message += "📋 *Последние события:*\n"
            for event in status['latest_events']:
                event_type = {
                    'startup': '🖥️ Запуск',
                    'login': '👤 Вход',
                    'privilege': '🔑 Привилегии',
                    'task': '⏰ Задача',
                    'service': '🔧 Служба',
                    'suspicious_process': '⚠️ Подозрительный процесс'
                }.get(event['type'], '❓ Другое')
                
                details = event['details']
                detail_str = ""
                
                if event['type'] == 'login' and 'username' in details:
                    detail_str = f" ({details['username']})"
                elif event['type'] == 'suspicious_process' and 'image' in details:
                    detail_str = f" ({details['image']})"
                
                message += f"• {event['time']} - {event_type}{detail_str}\n"
        else:
            message += "📋 *Последние события:* нет событий для отображения"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def _report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /report command."""
        if not self.event_handler:
            await update.message.reply_text("Отчет недоступен - обработчик событий не инициализирован")
            return
        
        # Get date parameter if provided
        date = None
        if context.args and len(context.args) > 0:
            date = context.args[0]
            
        report = self.event_handler.get_daily_report(date)
        
        if 'status' in report:
            await update.message.reply_text(report['status'])
            return
            
        # Generate report file
        date_str = report['date']
        report_format = self.config.get('reporting', {}).get('report_format', 'markdown')
        
        if report_format.lower() == 'pdf':
            report_file = self._generate_pdf_report(report)
            await self._send_document_async(report_file, f"Отчет за {date_str}")
            # Delete temporary file
            import os
            os.unlink(report_file)
        else:
            # Generate markdown report
            report_text = self._generate_markdown_report(report)
            await update.message.reply_text(report_text, parse_mode='Markdown')
    
    def _generate_markdown_report(self, report):
        """Generate a markdown report from the event data."""
        date_str = report['date']
        
        message = f"📊 *Отчет о событиях за {date_str}*\n\n"
        
        # Summary
        message += "*Сводка:*\n"
        message += f"🖥️ Запусков системы: {report['startup_count']}\n"
        message += f"👤 Входов в систему: {report['login_count']}\n"
        message += f"🔑 Повышений привилегий: {report['privilege_count']}\n"
        message += f"⏰ Изменений задач: {report['task_count']}\n"
        message += f"🔧 Изменений служб: {report['service_count']}\n"
        message += f"⚠️ Подозрительных процессов: {report['suspicious_process_count']}\n\n"
        
        # Details
        events = report['events']
        
        # First suspicious processes
        if events.get('suspicious_process'):
            message += "*⚠️ Подозрительные процессы:*\n"
            for process in events['suspicious_process'][:5]:  # Limit to 5
                image = process.get('image', 'Неизвестно')
                user = process.get('username', 'Неизвестно')
                time = process.get('time', 'Неизвестно')
                
                message += f"• {time} - `{image}` (Пользователь: {user})\n"
            
            if len(events['suspicious_process']) > 5:
                message += f"  _...и еще {len(events['suspicious_process']) - 5} процессов_\n"
            
            message += "\n"
        
        # Then services and tasks
        if events.get('service'):
            message += "*🔧 Изменения служб:*\n"
            for service in events['service'][:5]:  # Limit to 5
                name = service.get('service_name', 'Неизвестно')
                time = service.get('time', 'Неизвестно')
                
                message += f"• {time} - `{name}`\n"
            
            if len(events['service']) > 5:
                message += f"  _...и еще {len(events['service']) - 5} служб_\n"
            
            message += "\n"
        
        if events.get('task'):
            message += "*⏰ Изменения задач:*\n"
            for task in events['task'][:5]:  # Limit to 5
                name = task.get('task_name', 'Неизвестно')
                time = task.get('time', 'Неизвестно')
                
                message += f"• {time} - `{name}`\n"
            
            if len(events['task']) > 5:
                message += f"  _...и еще {len(events['task']) - 5} задач_\n"
            
            message += "\n"
        
        # Then logins
        if events.get('login'):
            message += "*👤 Входы в систему:*\n"
            for login in events['login'][:5]:  # Limit to 5
                username = login.get('username', 'Неизвестно')
                login_type = login.get('login_type', 'Неизвестно')
                time = login.get('time', 'Неизвестно')
                
                message += f"• {time} - `{username}` ({login_type})\n"
            
            if len(events['login']) > 5:
                message += f"  _...и еще {len(events['login']) - 5} входов_\n"
        
        return message
    
    def _generate_pdf_report(self, report):
        """Generate a PDF report from the event data."""
        date_str = report['date']
        
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Add title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f"Отчет о событиях за {date_str}", 0, 1, 'C')
        pdf.ln(10)
        
        # Add summary
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, "Сводка:", 0, 1)
        
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 8, f"Запусков системы: {report['startup_count']}", 0, 1)
        pdf.cell(0, 8, f"Входов в систему: {report['login_count']}", 0, 1)
        pdf.cell(0, 8, f"Повышений привилегий: {report['privilege_count']}", 0, 1)
        pdf.cell(0, 8, f"Изменений задач: {report['task_count']}", 0, 1)
        pdf.cell(0, 8, f"Изменений служб: {report['service_count']}", 0, 1)
        pdf.cell(0, 8, f"Подозрительных процессов: {report['suspicious_process_count']}", 0, 1)
        pdf.ln(10)
        
        # Add details
        events = report['events']
        
        # Suspicious processes section
        if events.get('suspicious_process'):
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Подозрительные процессы:", 0, 1)
            pdf.set_font('Arial', '', 12)
            
            for process in events['suspicious_process']:
                image = process.get('image', 'Неизвестно')
                user = process.get('username', 'Неизвестно')
                time = process.get('time', 'Неизвестно')
                reason = process.get('reason', 'Неизвестно')
                
                pdf.cell(0, 8, f"• {time} - {image}", 0, 1)
                pdf.cell(0, 8, f"  Пользователь: {user}", 0, 1)
                pdf.cell(0, 8, f"  Причина: {reason}", 0, 1)
                pdf.ln(5)
            
            pdf.ln(5)
        
        # Services section
        if events.get('service'):
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Изменения служб:", 0, 1)
            pdf.set_font('Arial', '', 12)
            
            for service in events['service']:
                name = service.get('service_name', 'Неизвестно')
                path = service.get('service_path', 'Неизвестно')
                time = service.get('time', 'Неизвестно')
                
                pdf.cell(0, 8, f"• {time} - {name}", 0, 1)
                pdf.cell(0, 8, f"  Путь: {path}", 0, 1)
                pdf.ln(5)
            
            pdf.ln(5)
        
        # Tasks section
        if events.get('task'):
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Изменения задач:", 0, 1)
            pdf.set_font('Arial', '', 12)
            
            for task in events['task']:
                name = task.get('task_name', 'Неизвестно')
                time = task.get('time', 'Неизвестно')
                
                pdf.cell(0, 8, f"• {time} - {name}", 0, 1)
                pdf.ln(5)
            
            pdf.ln(5)
        
        # Logins section
        if events.get('login'):
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Входы в систему:", 0, 1)
            pdf.set_font('Arial', '', 12)
            
            for login in events['login']:
                username = login.get('username', 'Неизвестно')
                login_type = login.get('login_type', 'Неизвестно')
                time = login.get('time', 'Неизвестно')
                
                pdf.cell(0, 8, f"• {time} - {username} ({login_type})", 0, 1)
            
            pdf.ln(5)
        
        # Generate the PDF file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        pdf.output(temp_file.name)
        
        return temp_file.name
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        message = """📋 *Доступные команды:*

/status - Показать текущий статус системы (аптайм, последние события)
/report [YYYY-MM-DD] - Получить отчет за день (по умолчанию - сегодня)
/help - Показать эту справку

Бот также отправляет уведомления о важных событиях в системе автоматически."""

        await update.message.reply_text(message, parse_mode='Markdown') 