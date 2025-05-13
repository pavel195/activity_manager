#!/bin/bash

# Скрипт для запуска Windows Monitor Agent в WSL

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "Запуск Windows Monitor Agent в WSL"

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker не установлен в WSL. Установите Docker перед запуском.${NC}"
    echo "Инструкция: https://docs.docker.com/engine/install/ubuntu/"
    exit 1
fi

# Проверка статуса Docker
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker не запущен в WSL. Запустите Docker перед выполнением скрипта.${NC}"
    echo "Запустите: sudo service docker start"
    exit 1
fi

# Проверка наличия Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Docker Compose не установлен в WSL. Устанавливаем...${NC}"
    sudo apt-get update
    sudo apt-get install -y docker-compose
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Не удалось установить Docker Compose. Установите вручную.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Docker Compose успешно установлен.${NC}"
fi

# Проверяем доступ к директории Windows
if [ ! -d "/mnt/c/Windows" ]; then
    echo -e "${RED}Не удалось получить доступ к директории Windows.${NC}"
    echo "Проверьте настройки WSL и права доступа."
    exit 1
fi

# Проверка доступа к Event Logs
if [ ! -d "/mnt/c/Windows/System32/winevt/Logs" ]; then
    echo -e "${RED}Не удалось получить доступ к Windows Event Logs.${NC}"
    echo "Проверьте настройки WSL и права доступа к C:\\Windows\\System32\\winevt\\Logs"
    exit 1
fi

# Проверяем наличие директорий
mkdir -p logs data
echo -e "${GREEN}Проверка директорий выполнена.${NC}"

# Проверяем наличие файла .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}Файл .env не найден. Создаем из шаблона...${NC}"
    cp dotenv.example .env
    echo -e "${GREEN}Создан файл .env.${NC}"
    echo -e "${YELLOW}Пожалуйста, отредактируйте файл .env и добавьте ваши учетные данные Telegram.${NC}"
    
    # Выводим содержимое .env
    echo -e "${CYAN}Содержимое файла .env:${NC}"
    cat .env
    
    echo -e "${YELLOW}Редактировать .env сейчас? (y/n)${NC}"
    read answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        nano .env
    else
        echo -e "${YELLOW}Не забудьте отредактировать .env перед использованием системы.${NC}"
    fi
fi

# Проверяем конфигурацию
if [ ! -f docker-compose.wsl.yml ]; then
    echo -e "${YELLOW}Файл docker-compose.wsl.yml не найден. Создаем...${NC}"
    
    cat > docker-compose.wsl.yml << 'EOL'
version: '3.8'

services:
  windows-monitor-agent:
    build:
      context: .
      dockerfile: Dockerfile
    image: windows-monitor-agent:latest
    container_name: windows-monitor-agent
    restart: unless-stopped
    volumes:
      - ./config.json:/app/config.json:ro
      - ./.env:/app/.env:ro
      - ./logs:/app/logs
      - ./data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock:ro
      # Монтируем Windows Event Logs через WSL
      - /mnt/c/Windows/System32/winevt/Logs:/winevt/Logs:ro
    environment:
      - TZ=Europe/Moscow
    privileged: true
    networks:
      - monitor-network

  log-viewer:
    image: amir20/dozzle:latest
    container_name: log-viewer
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    ports:
      - "8080:8080"
    networks:
      - monitor-network

networks:
  monitor-network:
    driver: bridge
EOL

    echo -e "${GREEN}Файл docker-compose.wsl.yml создан.${NC}"
fi

# Проверяем конфигурацию
if [ ! -f config.json ]; then
    echo -e "${YELLOW}Файл config.json не найден. Копируем docker-config.json...${NC}"
    cp docker-config.json config.json
    echo -e "${GREEN}Файл config.json создан.${NC}"
fi

# Запускаем сборку и запуск контейнеров
echo -e "${GREEN}Запуск Docker Compose...${NC}"
docker-compose -f docker-compose.wsl.yml build
docker-compose -f docker-compose.wsl.yml up -d

# Проверяем статус контейнеров
echo -e "${GREEN}Статус контейнеров:${NC}"
docker-compose -f docker-compose.wsl.yml ps

echo -e "\n${GREEN}Windows Monitor Agent запущен в WSL Docker.${NC}"
echo -e "${CYAN}Для просмотра логов используйте команду:${NC}"
echo -e "  docker-compose -f docker-compose.wsl.yml logs -f windows-monitor-agent"
echo -e "\n${CYAN}Веб-интерфейс для просмотра логов доступен по адресу:${NC}"
echo -e "  http://localhost:8080/" 