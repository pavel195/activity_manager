# Система мониторинга процессов Windows

Распределённое приложение для мониторинга запуска программ на Windows с централизованным сбором данных и уведомлениями в Telegram.

## Компоненты системы

### Агент (клиентская часть)
- Устанавливается на ПК пользователей под управлением Windows
- Отслеживает запуск определённых программ (Chrome, Yandex, Telegram, Проводник)
- Передаёт данные о событиях на сервер

### Сервер (централизованная часть)
- Принимает данные от агентов
- Сохраняет их в PostgreSQL и Elasticsearch
- Отправляет уведомления в Telegram

## Установка и настройка

### Запуск с использованием Makefile (рекомендуется)

#### Linux/macOS:

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/windows_manager.git
cd windows_manager
```

2. Настройте конфигурационные файлы:
   - `server/config/config.yaml` - настройки сервера
   - `agent/config/config.yaml` - настройки агента

3. Запустите серверную часть:
```bash
make server
```

4. Просмотр доступных команд:
```bash
make help
```

#### Windows:

1. Клонируйте репозиторий и перейдите в директорию проекта.

2. Настройте конфигурационные файлы:
   - `server/config/config.yaml` - настройки сервера
   - `agent/config/config.yaml` - настройки агента

3. Запустите агент:
```cmd
make agent
```

4. Просмотр доступных команд:
```cmd
make help
```

### Запуск с использованием Docker Compose

1. Запустите серверную часть:
```bash
docker-compose up -d postgres elasticsearch kibana server
```

2. Для запуска агента на Windows-машине:
```bash
cd agent
pip install -r requirements.txt
python src/main.py
```

### Ручная установка

#### Агент
```bash
cd agent
pip install -r requirements.txt
# Настройте config/config.yaml
python src/main.py
```

#### Сервер
```bash
cd server
pip install -r requirements.txt
# Настройте config/config.yaml
python src/main.py
```

## Доступ к компонентам

- **API сервера**: http://localhost:8000
- **Kibana**: http://localhost:5601
- **Elasticsearch**: http://localhost:9200

## Требования
- Python 3.8+
- PostgreSQL
- Elasticsearch
- Доступ к Telegram Bot API
- Docker и Docker Compose (для запуска в контейнерах)

## Структура проекта

```
windows_manager/
├── agent/                  # Клиентская часть (агент)
│   ├── config/             # Конфигурационные файлы агента
│   ├── src/                # Исходный код агента
│   ├── Dockerfile          # Dockerfile для сборки агента
│   └── requirements.txt    # Зависимости агента
├── server/                 # Серверная часть
│   ├── config/             # Конфигурационные файлы сервера
│   ├── src/                # Исходный код сервера
│   │   ├── api/            # API модуль
│   │   ├── db/             # Модуль базы данных
│   │   └── telegram/       # Модуль Telegram
│   ├── Dockerfile          # Dockerfile для сборки сервера
│   └── requirements.txt    # Зависимости сервера
├── Makefile                # Makefile для Linux/macOS
├── Makefile.win            # Makefile для Windows
├── make.bat                # Скрипт запуска Makefile.win
└── docker-compose.yml      # Конфигурация Docker Compose
``` 