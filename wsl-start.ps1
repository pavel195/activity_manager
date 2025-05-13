# Скрипт для запуска Windows Monitor Agent в WSL

# Проверка наличия WSL
if (-not (Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Host "WSL не установлен. Установите WSL перед запуском." -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Проверяем права администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Для доступа к Windows Event Logs требуются права администратора." -ForegroundColor Red
    Write-Host "Запустите PowerShell от имени администратора и повторите запуск скрипта." -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Проверка наличия Docker в WSL
try {
    $dockerCheck = wsl docker --version
    if (-not $dockerCheck) {
        Write-Host "Docker не установлен в WSL. Установите Docker в WSL перед запуском." -ForegroundColor Red
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
} catch {
    Write-Host "Ошибка при проверке Docker в WSL: $_" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Проверяем наличие директорий
if (-not (Test-Path logs)) {
    New-Item -ItemType Directory -Path logs | Out-Null
    Write-Host "Создана директория logs" -ForegroundColor Green
}
if (-not (Test-Path data)) {
    New-Item -ItemType Directory -Path data | Out-Null
    Write-Host "Создана директория data" -ForegroundColor Green
}

# Проверяем наличие файла .env
if (-not (Test-Path .env)) {
    Write-Host "Файл .env не найден. Создаем из шаблона..." -ForegroundColor Yellow
    Copy-Item dotenv.example .env
    Write-Host "Создан файл .env. Пожалуйста, отредактируйте его и добавьте ваши учетные данные Telegram." -ForegroundColor Green
    notepad .env
    Read-Host "После редактирования .env нажмите Enter для продолжения"
}

# Проверяем конфигурацию
if (-not (Test-Path config.json)) {
    Write-Host "Файл config.json не найден. Копируем docker-config.json..." -ForegroundColor Yellow
    Copy-Item docker-config.json config.json
    Write-Host "Создан файл config.json" -ForegroundColor Green
}

# Создаем модифицированный docker-compose для WSL
$dockerComposeContent = @"
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
"@

$dockerComposeContent | Out-File -FilePath "docker-compose.wsl.yml" -Encoding utf8
Write-Host "Создан файл docker-compose.wsl.yml для WSL" -ForegroundColor Green

Write-Host "Запуск Docker Compose в WSL..." -ForegroundColor Green

# Получаем текущий путь
$currentPath = (Get-Location).Path
# Конвертируем Windows путь в формат WSL (/mnt/c/...)
$wslPath = wsl wslpath "$currentPath"

# Запускаем Docker Compose в WSL
$wslCommand = @"
cd "$wslPath" && 
docker-compose -f docker-compose.wsl.yml build && 
docker-compose -f docker-compose.wsl.yml up -d
"@

wsl bash -c "$wslCommand"

Write-Host ""
Write-Host "Windows Monitor Agent запущен в WSL Docker." -ForegroundColor Green
Write-Host "Для просмотра логов используйте команду в WSL:" -ForegroundColor Cyan
Write-Host "  docker-compose -f docker-compose.wsl.yml logs -f windows-monitor-agent" -ForegroundColor White
Write-Host ""
Write-Host "Веб-интерфейс для просмотра логов доступен по адресу:" -ForegroundColor Cyan
Write-Host "  http://localhost:8080/" -ForegroundColor White

# Проверяем статус контейнеров
Write-Host ""
Write-Host "Статус контейнеров:" -ForegroundColor Green
wsl bash -c "cd '$wslPath' && docker-compose -f docker-compose.wsl.yml ps"

Read-Host "Нажмите Enter для завершения" 