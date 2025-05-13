#!/bin/bash

# Скрипт для установки и настройки Sysmon под Windows (через WSL/Bash)
# Требует запуска с правами администратора Windows

set -e

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Установка и настройка Sysmon${NC}"
echo "=============================="

# Проверка наличия инструментов
check_tools() {
    echo -e "${YELLOW}Проверка наличия необходимых инструментов...${NC}"
    
    # Проверяем наличие curl
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}curl не найден! Пожалуйста, установите curl.${NC}"
        exit 1
    fi
    
    # Проверяем наличие unzip
    if ! command -v unzip &> /dev/null; then
        echo -e "${RED}unzip не найден! Пожалуйста, установите unzip.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Все необходимые инструменты найдены.${NC}"
}

# Создание директорий
create_directories() {
    echo -e "${YELLOW}Создание необходимых директорий...${NC}"
    
    # Создаем директорию для инструментов
    mkdir -p "/mnt/c/ProgramData/WindowsMonitor/tools"
    
    echo -e "${GREEN}Директории созданы.${NC}"
}

# Загрузка Sysmon
download_sysmon() {
    echo -e "${YELLOW}Загрузка Sysmon...${NC}"
    
    # Создаем временную директорию
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    # Загружаем Sysmon с официального сайта Microsoft
    curl -L -o Sysmon.zip "https://download.sysinternals.com/files/Sysmon.zip"
    
    # Распаковываем архив
    unzip Sysmon.zip
    
    # Копируем файлы в целевую директорию
    cp Sysmon64.exe "/mnt/c/ProgramData/WindowsMonitor/tools/Sysmon.exe"
    
    # Очищаем временную директорию
    cd - > /dev/null
    rm -rf "$TMP_DIR"
    
    echo -e "${GREEN}Sysmon загружен и скопирован.${NC}"
}

# Копирование конфигурации
copy_config() {
    echo -e "${YELLOW}Копирование конфигурации Sysmon...${NC}"
    
    # Определяем директорию скрипта
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
    
    # Определяем корневую директорию проекта
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    
    # Проверяем наличие конфигурации
    CONFIG_FILE="$PROJECT_ROOT/sysmon_config.xml"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}Конфигурационный файл не найден: $CONFIG_FILE${NC}"
        exit 1
    fi
    
    # Копируем конфигурацию
    cp "$CONFIG_FILE" "/mnt/c/ProgramData/WindowsMonitor/tools/sysmon_config.xml"
    
    echo -e "${GREEN}Конфигурация скопирована.${NC}"
}

# Установка Sysmon
install_sysmon() {
    echo -e "${YELLOW}Установка Sysmon...${NC}"
    
    # Запускаем Sysmon с нужными параметрами
    # Используем cmd.exe для запуска с правами администратора
    # Обратите внимание, что это может требовать подтверждения UAC
    
    powershell.exe -Command "Start-Process -FilePath 'C:\\ProgramData\\WindowsMonitor\\tools\\Sysmon.exe' -ArgumentList '-i', 'C:\\ProgramData\\WindowsMonitor\\tools\\sysmon_config.xml', '-accepteula' -Verb RunAs"
    
    echo -e "${GREEN}Команда установки Sysmon выполнена.${NC}"
    echo -e "${YELLOW}Примечание: Если запрос на повышение привилегий появился, подтвердите его.${NC}"
}

# Проверка службы Sysmon
check_sysmon_service() {
    echo -e "${YELLOW}Проверка службы Sysmon...${NC}"
    
    # Проверяем статус службы
    SERVICE_STATUS=$(powershell.exe -Command "Get-Service -Name Sysmon -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status")
    
    if [ -z "$SERVICE_STATUS" ]; then
        echo -e "${RED}Служба Sysmon не найдена! Возможно, установка не удалась.${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Служба Sysmon установлена и имеет статус: $SERVICE_STATUS${NC}"
    return 0
}

# Основная функция
main() {
    echo -e "${YELLOW}Начало установки Sysmon...${NC}"
    
    check_tools
    create_directories
    download_sysmon
    copy_config
    install_sysmon
    
    # Даем время на установку службы
    echo -e "${YELLOW}Ожидание завершения установки (10 секунд)...${NC}"
    sleep 10
    
    # Проверяем установку
    if check_sysmon_service; then
        echo -e "${GREEN}Установка Sysmon завершена успешно!${NC}"
    else
        echo -e "${RED}Проверьте логи и попробуйте установить Sysmon вручную.${NC}"
        echo "Команда для ручной установки:"
        echo "C:\\ProgramData\\WindowsMonitor\\tools\\Sysmon.exe -i C:\\ProgramData\\WindowsMonitor\\tools\\sysmon_config.xml -accepteula"
    fi
}

# Запуск основной функции
main 