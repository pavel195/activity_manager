import win32evtlog
import win32evtlogutil
import win32con
import win32security
import datetime
import time
import threading
import logging

class EventMonitor:
    def __init__(self, config, event_handler):
        self.config = config
        self.event_handler = event_handler
        self.running = False
        self.thread = None
        self.event_sources = {
            'System': ['Service Control Manager', 'Microsoft-Windows-Power-Troubleshooter'],
            'Security': [],
            'Microsoft-Windows-Sysmon/Operational': []
        }
        self.event_ids = {
            'startup': [6005, 6009],  # Startup events
            'login': [4624],          # Login events
            'privileges': [4672],     # Privilege elevation
            'task': [4698, 4699],     # Scheduled task creation/deletion
            'service': [7045, 7040],  # Service install/modification
            'sysmon_process': [1],    # Sysmon Process creation
            'sysmon_network': [3]     # Sysmon Network connection
        }
        self.last_read_time = {log: int(time.time()) for log in self.event_sources}
        self.setup_logging()
        
    def setup_logging(self):
        self.logger = logging.getLogger("EventMonitor")
        self.logger.setLevel(logging.INFO)
        
    def start(self):
        if self.running:
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.logger.info("Event monitoring started")
        return True
        
    def stop(self):
        if not self.running:
            return False
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        self.logger.info("Event monitoring stopped")
        return True
    
    def _monitor_loop(self):
        while self.running:
            try:
                for log_type, sources in self.event_sources.items():
                    self._check_log(log_type, sources)
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {str(e)}")
            
            time.sleep(10)  # Check every 10 seconds
    
    def _check_log(self, log_type, sources):
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        handle = win32evtlog.OpenEventLog(None, log_type)
        
        try:
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            if events:
                for event in events:
                    event_time = int(event.TimeGenerated.timestamp())
                    
                    # Skip older events
                    if event_time <= self.last_read_time[log_type]:
                        continue
                    
                    self.last_read_time[log_type] = event_time
                    
                    if not sources or event.SourceName in sources:
                        self._process_event(log_type, event)
        finally:
            win32evtlog.CloseEventLog(handle)
    
    def _process_event(self, log_type, event):
        event_id = event.EventID & 0xFFFF  # The real event ID is the lower 16 bits
        
        event_data = {
            'log_type': log_type,
            'source': event.SourceName,
            'event_id': event_id,
            'time': event.TimeGenerated.strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp': int(event.TimeGenerated.timestamp()),
            'computer': event.ComputerName,
            'description': win32evtlogutil.SafeFormatMessage(event, log_type)
        }
        
        # Process depending on event type
        if event_id in self.event_ids['startup'] and self.config['features'].get('track_services', True):
            self.event_handler.handle_system_startup(event_data)
            
        elif event_id in self.event_ids['login'] and self.config['features'].get('track_logins', True):
            # Parsing login events requires additional logic
            if log_type == 'Security':
                self._parse_login_event(event, event_data)
                
        elif event_id in self.event_ids['privileges'] and self.config['features'].get('track_logins', True):
            self.event_handler.handle_privilege_elevation(event_data)
            
        elif event_id in self.event_ids['task'] and self.config['features'].get('track_services', True):
            self.event_handler.handle_scheduled_task(event_data)
            
        elif event_id in self.event_ids['service'] and self.config['features'].get('track_services', True):
            self.event_handler.handle_service_change(event_data)
            
        elif event_id in self.event_ids['sysmon_process'] and self.config['features'].get('track_processes', True):
            self._parse_sysmon_process(event, event_data)
            
        elif event_id in self.event_ids['sysmon_network'] and self.config['features'].get('track_processes', True):
            self._parse_sysmon_network(event, event_data)
    
    def _parse_login_event(self, event, event_data):
        try:
            # Extract login type and user info
            # For login events (4624), parse user and login type
            event_data['login_type'] = None
            event_data['username'] = None
            
            if event.StringInserts:
                for i, data in enumerate(event.StringInserts):
                    if i == 8:  # Login type
                        event_data['login_type'] = data
                    elif i == 5:  # Account Name
                        event_data['username'] = data
            
            # Filter only interactive, RDP, and unlock logins (types 2, 10, 7)
            if event_data['login_type'] in ['2', '7', '10']:
                self.event_handler.handle_user_login(event_data)
                
        except Exception as e:
            self.logger.error(f"Error parsing login event: {str(e)}")
    
    def _parse_sysmon_process(self, event, event_data):
        try:
            if event.StringInserts:
                # Extract process information
                event_data['process'] = {
                    'image': event.StringInserts[3] if len(event.StringInserts) > 3 else '',
                    'command_line': event.StringInserts[10] if len(event.StringInserts) > 10 else '',
                    'parent_image': event.StringInserts[13] if len(event.StringInserts) > 13 else '',
                    'user': event.StringInserts[6] if len(event.StringInserts) > 6 else ''
                }
                
                self.event_handler.handle_process_creation(event_data)
                
        except Exception as e:
            self.logger.error(f"Error parsing Sysmon process event: {str(e)}")
    
    def _parse_sysmon_network(self, event, event_data):
        try:
            if event.StringInserts:
                # Extract network connection information
                event_data['network'] = {
                    'image': event.StringInserts[3] if len(event.StringInserts) > 3 else '',
                    'protocol': event.StringInserts[7] if len(event.StringInserts) > 7 else '',
                    'src_ip': event.StringInserts[8] if len(event.StringInserts) > 8 else '',
                    'src_port': event.StringInserts[9] if len(event.StringInserts) > 9 else '',
                    'dst_ip': event.StringInserts[14] if len(event.StringInserts) > 14 else '',
                    'dst_port': event.StringInserts[15] if len(event.StringInserts) > 15 else ''
                }
                
                self.event_handler.handle_network_connection(event_data)
                
        except Exception as e:
            self.logger.error(f"Error parsing Sysmon network event: {str(e)}") 