import os
import json
import logging
import datetime
from pathlib import Path
import requests
import clamd
import psutil

class EventHandler:
    def __init__(self, config, telegram_notifier):
        self.config = config
        self.telegram = telegram_notifier
        self.today_events = {
            'startup': [],
            'login': [],
            'privilege': [],
            'task': [],
            'service': [],
            'suspicious_process': []
        }
        self.today_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.storage_path = Path('./data/events')
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.process_whitelist = set(self.config['monitoring'].get('process_whitelist', []))
        self.service_whitelist = set(self.config['monitoring'].get('service_whitelist', []))
        self.task_whitelist = set(self.config['monitoring'].get('task_whitelist', []))
        
        self.vt_api_key = self.config.get('vt_api_key', '')
        self.clamav_enabled = False
        
        self.setup_logging()
        self.try_setup_clamav()
    
    def setup_logging(self):
        self.logger = logging.getLogger('EventHandler')
        self.logger.setLevel(logging.INFO)
    
    def try_setup_clamav(self):
        try:
            self.clamav = clamd.ClamdNetworkSocket()
            self.clamav.ping()
            self.clamav_enabled = True
            self.logger.info("ClamAV connection established")
        except Exception as e:
            self.logger.warning(f"ClamAV connection failed, virus scanning disabled: {str(e)}")
            self.clamav_enabled = False
    
    def handle_system_startup(self, event_data):
        self.logger.info(f"System startup detected: {event_data['time']}")
        
        self.today_events['startup'].append({
            'time': event_data['time'],
            'description': event_data['description']
        })
        
        self._save_event_data()
        
        # Send notification to Telegram
        message = f"🖥️ Обнаружено включение компьютера\nВремя: {event_data['time']}\nКомпьютер: {event_data['computer']}"
        self.telegram.send_message(message)
    
    def handle_user_login(self, event_data):
        login_type_str = {
            '2': 'Интерактивный',
            '7': 'Разблокировка',
            '10': 'Удаленный доступ (RDP)'
        }.get(event_data.get('login_type', ''), 'Неизвестный')
        
        username = event_data.get('username', 'Неизвестный пользователь')
        
        self.logger.info(f"User login: {username} ({login_type_str}) at {event_data['time']}")
        
        self.today_events['login'].append({
            'time': event_data['time'],
            'username': username,
            'login_type': login_type_str,
            'description': event_data['description']
        })
        
        self._save_event_data()
        
        # Send notification to Telegram
        message = f"👤 Вход в систему\nПользователь: {username}\nТип входа: {login_type_str}\nВремя: {event_data['time']}"
        self.telegram.send_message(message)
    
    def handle_privilege_elevation(self, event_data):
        if 'username' not in event_data:
            event_data['username'] = 'Неизвестный пользователь'
        
        self.logger.info(f"Privilege elevation: {event_data['username']} at {event_data['time']}")
        
        self.today_events['privilege'].append({
            'time': event_data['time'],
            'username': event_data['username'],
            'description': event_data['description']
        })
        
        self._save_event_data()
        
        # Send notification to Telegram, but only if it's not a normal system process
        message = f"🔑 Повышение привилегий\nПользователь: {event_data['username']}\nВремя: {event_data['time']}"
        self.telegram.send_message(message)
    
    def handle_scheduled_task(self, event_data):
        # Extract task name from description (task events have a specific format)
        task_name = "Неизвестная задача"
        
        if 'Task Name:' in event_data['description']:
            task_name_start = event_data['description'].find('Task Name:')
            task_name_end = event_data['description'].find('\n', task_name_start)
            if task_name_end == -1:
                task_name_end = len(event_data['description'])
            
            task_name = event_data['description'][task_name_start+11:task_name_end].strip()
        
        # Skip if in whitelist
        if task_name in self.task_whitelist:
            return
        
        self.logger.info(f"Scheduled task change: {task_name} at {event_data['time']}")
        
        self.today_events['task'].append({
            'time': event_data['time'],
            'task_name': task_name,
            'event_id': event_data['event_id'],
            'description': event_data['description']
        })
        
        self._save_event_data()
        
        # Send notification to Telegram
        operation = "создана" if event_data['event_id'] == 4698 else "изменена"
        message = f"⏰ Задача планировщика {operation}\nИмя задачи: {task_name}\nВремя: {event_data['time']}"
        self.telegram.send_message(message)
    
    def handle_service_change(self, event_data):
        # Extract service name from description
        service_name = "Неизвестная служба"
        service_path = "Неизвестный путь"
        
        # Service creation events (7045) have specific format
        if event_data['event_id'] == 7045 and event_data['description']:
            lines = event_data['description'].split('\n')
            for line in lines:
                if line.startswith('Service Name:'):
                    service_name = line[14:].strip()
                elif line.startswith('Service File Name:'):
                    service_path = line[19:].strip()
                    
        # Skip if in whitelist
        if service_name in self.service_whitelist:
            return
        
        self.logger.info(f"Service change: {service_name} at {event_data['time']}")
        
        self.today_events['service'].append({
            'time': event_data['time'],
            'service_name': service_name,
            'service_path': service_path,
            'event_id': event_data['event_id'],
            'description': event_data['description']
        })
        
        self._save_event_data()
        
        # Check if service executable is suspicious
        is_suspicious = False
        if os.path.exists(service_path):
            is_suspicious = self._check_file_suspicious(service_path)
        
        # Send notification to Telegram
        operation = "установлена" if event_data['event_id'] == 7045 else "изменена"
        message = f"🔧 Служба Windows {operation}\nИмя службы: {service_name}\nПуть: {service_path}\nВремя: {event_data['time']}"
        
        if is_suspicious:
            message += "\n⚠️ Служба помечена как подозрительная!"
            
        self.telegram.send_message(message)
    
    def handle_process_creation(self, event_data):
        if 'process' not in event_data:
            return
            
        process = event_data['process']
        image_path = process.get('image', '')
        command_line = process.get('command_line', '')
        username = process.get('user', 'Неизвестный')
        
        # Skip if in whitelist
        if self._is_process_whitelisted(image_path):
            return
        
        # Check if process is suspicious
        is_suspicious = self._is_process_suspicious(image_path, command_line)
        
        if is_suspicious:
            self.logger.warning(f"Suspicious process: {image_path} by {username} at {event_data['time']}")
            
            self.today_events['suspicious_process'].append({
                'time': event_data['time'],
                'image': image_path,
                'command_line': command_line,
                'username': username,
                'reason': 'Suspicious process behavior or location'
            })
            
            self._save_event_data()
            
            # Check if file is malicious
            malware_result = self._check_file_suspicious(image_path)
            
            # Send notification to Telegram
            message = f"⚠️ Подозрительный процесс\nПроцесс: {os.path.basename(image_path)}\nПуть: {image_path}\nПользователь: {username}\nВремя: {event_data['time']}"
            
            if malware_result:
                message += f"\n🚨 Результат проверки: {malware_result}"
                
            self.telegram.send_message(message)
    
    def handle_network_connection(self, event_data):
        if 'network' not in event_data:
            return
            
        network = event_data['network']
        image_path = network.get('image', '')
        dst_ip = network.get('dst_ip', '')
        dst_port = network.get('dst_port', '')
        
        # Check if network connection is suspicious
        is_suspicious = self._is_network_suspicious(image_path, dst_ip, dst_port)
        
        if is_suspicious:
            self.logger.warning(f"Suspicious network connection: {image_path} -> {dst_ip}:{dst_port} at {event_data['time']}")
            
            # We could add this to a separate category of events
            self.today_events['suspicious_process'].append({
                'time': event_data['time'],
                'image': image_path,
                'connection': f"{dst_ip}:{dst_port}",
                'reason': 'Suspicious network connection'
            })
            
            self._save_event_data()
            
            # Send notification to Telegram
            message = f"🌐 Подозрительное сетевое соединение\nПроцесс: {os.path.basename(image_path)}\nНазначение: {dst_ip}:{dst_port}\nВремя: {event_data['time']}"
            self.telegram.send_message(message)
    
    def _is_process_whitelisted(self, image_path):
        if not image_path:
            return False
            
        # Check exact match
        if image_path in self.process_whitelist:
            return True
            
        # Check basename match
        basename = os.path.basename(image_path).lower()
        if basename in (os.path.basename(p).lower() for p in self.process_whitelist):
            return True
            
        return False
    
    def _is_process_suspicious(self, image_path, command_line):
        if not image_path:
            return False
            
        # Check for processes running from suspicious locations
        suspicious_locations = [
            r'\temp\\', r'\windows\temp\\', r'\appdata\local\temp\\',
            r'\users\public\\', r'\programdata\\', r'\downloads\\'
        ]
        
        image_path_lower = image_path.lower()
        
        for location in suspicious_locations:
            if location in image_path_lower:
                return True
                
        # Check for suspicious command line arguments
        suspicious_args = [
            '-enc', '-encodedcommand', '-windowstyle hidden', 
            'iex(', 'invoke-expression', 'downloadstring',
            'bypass', 'hidden', 'webclient'
        ]
        
        if command_line:
            command_line_lower = command_line.lower()
            for arg in suspicious_args:
                if arg in command_line_lower:
                    return True
        
        return False
    
    def _is_network_suspicious(self, image_path, dst_ip, dst_port):
        # Suspicious ports
        suspicious_ports = ['4444', '1337', '31337', '8080', '8000']
        
        if dst_port in suspicious_ports:
            return True
            
        # Could add more checks here, like IP reputation lookup
        return False
    
    def _check_file_suspicious(self, file_path):
        if not os.path.exists(file_path):
            return False
            
        result = ""
        
        # Try ClamAV first
        if self.clamav_enabled:
            try:
                scan_result = self.clamav.scan_file(file_path)
                if scan_result and file_path in scan_result:
                    if scan_result[file_path][0] == 'FOUND':
                        result = f"ClamAV: {scan_result[file_path][1]}"
                        return result
            except Exception as e:
                self.logger.error(f"ClamAV scan error: {str(e)}")
        
        # Try VirusTotal if API key provided
        if self.vt_api_key:
            try:
                file_hash = self._get_file_hash(file_path)
                vt_result = self._check_virustotal(file_hash)
                if vt_result:
                    result = f"VirusTotal: {vt_result}"
                    return result
            except Exception as e:
                self.logger.error(f"VirusTotal check error: {str(e)}")
        
        return result
    
    def _get_file_hash(self, file_path):
        import hashlib
        
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
                
        return sha256_hash.hexdigest()
    
    def _check_virustotal(self, file_hash):
        if not self.vt_api_key:
            return None
            
        url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
        headers = {
            "x-apikey": self.vt_api_key
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if 'data' in result and 'attributes' in result['data']:
                    stats = result['data']['attributes'].get('last_analysis_stats', {})
                    malicious = stats.get('malicious', 0)
                    suspicious = stats.get('suspicious', 0)
                    total = sum(stats.values())
                    
                    if malicious > 0 or suspicious > 0:
                        return f"Обнаружено {malicious} вредоносных и {suspicious} подозрительных детектирований из {total}"
            
            return None
        except Exception as e:
            self.logger.error(f"VirusTotal API error: {str(e)}")
            return None
    
    def _save_event_data(self):
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Reset events if day changed
        if current_date != self.today_date:
            self.today_events = {
                'startup': [],
                'login': [],
                'privilege': [],
                'task': [],
                'service': [],
                'suspicious_process': []
            }
            self.today_date = current_date
        
        # Save to JSON file
        file_path = self.storage_path / f"events_{current_date}.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.today_events, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving event data: {str(e)}")
    
    def get_system_status(self):
        # Get system uptime
        uptime_seconds = int(psutil.boot_time())
        uptime_datetime = datetime.datetime.fromtimestamp(uptime_seconds)
        uptime_str = (datetime.datetime.now() - uptime_datetime).total_seconds()
        
        # Format uptime
        days, remainder = divmod(uptime_str, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        uptime_formatted = f"{int(days)}д {int(hours)}ч {int(minutes)}м"
        
        # Get latest events
        latest_events = []
        
        for category in self.today_events:
            events = self.today_events[category]
            for event in events:
                if 'time' in event:
                    latest_events.append({
                        'type': category,
                        'time': event['time'],
                        'details': event
                    })
        
        # Sort by time (latest first)
        latest_events.sort(key=lambda x: x['time'], reverse=True)
        
        # Take only 5 latest events
        latest_events = latest_events[:5]
        
        return {
            'uptime': uptime_formatted,
            'uptime_since': uptime_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'current_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'latest_events': latest_events,
            'hostname': os.environ.get('COMPUTERNAME', 'Unknown')
        }
    
    def get_daily_report(self, date=None):
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
            
        try:
            file_path = self.storage_path / f"events_{date}.json"
            
            if not file_path.exists():
                return {
                    'date': date,
                    'status': 'Отчет недоступен - нет данных за указанную дату'
                }
                
            with open(file_path, 'r', encoding='utf-8') as f:
                events = json.load(f)
                
            # Calculate statistics
            stats = {
                'date': date,
                'startup_count': len(events.get('startup', [])),
                'login_count': len(events.get('login', [])),
                'privilege_count': len(events.get('privilege', [])),
                'task_count': len(events.get('task', [])),
                'service_count': len(events.get('service', [])),
                'suspicious_process_count': len(events.get('suspicious_process', [])),
                'events': events
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting daily report: {str(e)}")
            return {
                'date': date,
                'status': 'Ошибка при формировании отчета'
            } 