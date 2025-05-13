# Windows Monitor Agent

Система мониторинга активности на ПК под управлением Windows и отправки уведомлений в Telegram.

## Возможности

- Мониторинг и уведомления о ключевых событиях Windows:
  - Включение компьютера
  - Вход пользователей в систему
  - Запуск подозрительных процессов
  - Установка новых служб
  - Создание задач в планировщике
  
- Telegram бот с командами:
  - `/status` - текущий статус системы и последние события
  - `/report` - отчет о событиях за день
  - `/help` - справка

- Обнаружение подозрительной активности:
  - Проверка процессов на подозрительные признаки
  - Интеграция с ClamAV и VirusTotal
  
- Ежедневные отчеты

## Системные требования

- Windows 10/11 или Windows Server 2016/2019/2022
- Python 3.7+
- Права администратора для установки

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/windows-monitor-agent.git
cd windows-monitor-agent
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка конфигурации

#### Метод 1: Использование .env файла (рекомендуется)

Создайте файл `.env` в корне проекта на основе примера `dotenv.example`:

```bash
cp dotenv.example .env
```

Отредактируйте файл `.env` и добавьте ваши данные:

```
# Telegram API
TELEGRAM_TOKEN=ваш_токен_бота
CHAT_ID=ваш_id_чата

# VirusTotal API (опционально)
VT_API_KEY=ваш_ключ_api
```

#### Метод 2: Использование config.json

Откройте файл `config.json` и внесите необходимые изменения:

```json
{
  "telegram_token": "YOUR_TELEGRAM_BOT_TOKEN",
  "chat_id": "YOUR_TELEGRAM_CHAT_ID",
  "vt_api_key": "YOUR_VIRUSTOTAL_API_KEY", (опционально)
  "features": {
    "track_processes": true,
    "track_services": true,
    "track_logins": true,
    "daily_report": true
  }
}
```

> **Примечание**: Если одновременно настроены оба файла (`.env` и `config.json`), значения из `.env` имеют приоритет.

Для получения `telegram_token` создайте бота через [@BotFather](https://t.me/BotFather).
Для получения `chat_id` отправьте сообщение боту [@getidsbot](https://t.me/getidsbot).

### 4. Установка Sysmon (опционально, рекомендуется)

1. Загрузите [Sysmon](https://docs.microsoft.com/en-us/sysinternals/downloads/sysmon) от Microsoft Sysinternals
2. Скопируйте `Sysmon.exe` в `C:/ProgramData/WindowsMonitor/tools/`
3. Запустите установку командой:

```bash
python scripts/install_service.py --sysmon
```

### 5. Установка агента как службы Windows

```bash
python scripts/install_service.py --install
```

## Ручной запуск

Для запуска агента без установки службы:

```bash
python src/agent/main.py --config config.json --log-dir ./logs
```

## Удаление

Для удаления службы:

```bash
python scripts/install_service.py --uninstall
```

## Структура проекта

```
windows-monitor-agent/
├── config.json                # Конфигурация агента
├── requirements.txt           # Зависимости Python
├── sysmon_config.xml          # Конфигурация Sysmon
├── src/                       # Исходный код
│   └── agent/                 # Модули агента
│       ├── __init__.py
│       ├── main.py            # Основной модуль
│       ├── event_monitor.py   # Мониторинг событий
│       ├── event_handler.py   # Обработчик событий
│       └── telegram_notifier.py # Telegram интеграция
├── scripts/                   # Скрипты установки
│   └── install_service.py     # Установка службы Windows
└── data/                      # Директория для данных
    └── events/                # Сохраненные события
```

## Лицензия

MIT 