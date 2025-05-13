# Docker-версия Windows Monitor Agent

Данное руководство описывает запуск Windows Monitor Agent с использованием Docker и Docker Compose.

## Предварительные требования

1. Установленный Docker Desktop для Windows
2. Доступ к Windows API (для мониторинга событий)
3. Права администратора для доступа к системным логам

## Быстрый старт

### 1. Подготовка конфигурации

Скопируйте пример файла .env:

```bash
cp dotenv.example .env
```

Отредактируйте файл `.env` и добавьте следующие переменные:

```
TELEGRAM_TOKEN=ваш_токен_бота
CHAT_ID=ваш_идентификатор_чата
VT_API_KEY=ваш_ключ_virustotal (опционально)
```

### 2. Сборка и запуск

```bash
docker-compose up -d
```

Это действие:
- Соберет Docker-образ с Windows Monitor Agent
- Запустит контейнер с агентом мониторинга
- Запустит контейнер с веб-интерфейсом для просмотра логов (опционально)

### 3. Просмотр логов

```bash
docker-compose logs -f windows-monitor-agent
```

Также вы можете открыть веб-интерфейс по адресу: http://localhost:8080/

## Структура Docker-проекта

- `docker-compose.yml` - конфигурация Docker Compose для запуска контейнеров
- `Dockerfile` - инструкции для сборки образа
- `docker_entrypoint.py` - точка входа для контейнера
- `docker-config.json` - конфигурация для Docker-версии агента

## Особенности Docker-версии

### Доступ к Windows Event Logs

Чтобы агент мог получать доступ к Windows Event Logs, в docker-compose.yml настроено монтирование директории `C:/Windows/System32/winevt/Logs` в контейнер.

### Хранение данных

- Логи агента монитора хранятся в директории `./logs`
- Данные о событиях хранятся в директории `./data`
- Конфигурация контейнера монтируется из `./config.json` и `./.env`

### Перезагрузка и обновление

Для перезагрузки агента после изменения конфигурации:

```bash
docker-compose restart windows-monitor-agent
```

Для обновления образа и перезапуска контейнеров:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Устранение неполадок

### Проблемы с доступом к Windows Event Logs

Убедитесь, что Docker Desktop имеет доступ к директории `C:/Windows/System32/winevt/Logs`. Возможно, потребуется запустить Docker Desktop с правами администратора.

### Проблемы с доступом к Telegram API

Проверьте настройки в файле `.env`. Возможно, требуется обновить токен бота или идентификатор чата.

### Мониторинг контейнера

Для просмотра состояния контейнера используйте:

```bash
docker-compose ps
```

### Вывод всех логов

```bash
docker-compose logs --tail=100
``` 