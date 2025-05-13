#!/bin/bash

# Проверка наличия Docker и Docker Compose
if ! command -v docker &> /dev/null; then
    echo "Docker не установлен. Установите Docker перед запуском."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "Docker не запущен. Запустите Docker Desktop перед выполнением скрипта."
    exit 1
fi

# Проверяем наличие файла .env
if [ ! -f .env ]; then
    echo "Файл .env не найден. Создаем из шаблона..."
    cp dotenv.example .env
    echo "Создан файл .env. Пожалуйста, отредактируйте его и добавьте ваши учетные данные Telegram."
    echo "Затем запустите скрипт повторно."
    exit 1
fi

# Проверяем наличие директорий
mkdir -p logs data

# Проверяем конфигурацию
if [ ! -f config.json ]; then
    echo "Файл config.json не найден. Копируем docker-config.json..."
    cp docker-config.json config.json
fi

# Проверяем права на чтение Windows Event Logs
echo "Для доступа к Windows Event Logs требуются права администратора."
echo "Нажмите Enter, чтобы продолжить..."
read

# Запускаем сборку и запуск контейнеров
echo "Запуск Docker Compose..."
docker-compose up -d

# Проверяем статус контейнеров
echo "Статус контейнеров:"
docker-compose ps

echo ""
echo "Windows Monitor Agent запущен в Docker."
echo "Для просмотра логов используйте команду:"
echo "  docker-compose logs -f windows-monitor-agent"
echo ""
echo "Веб-интерфейс для просмотра логов доступен по адресу:"
echo "  http://localhost:8080/" 