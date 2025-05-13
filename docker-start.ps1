# Проверка наличия Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker не установлен. Установите Docker Desktop перед запуском." -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Проверка запущен ли Docker
try {
    docker info | Out-Null
} catch {
    Write-Host "Docker не запущен. Запустите Docker Desktop перед выполнением скрипта." -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Проверяем наличие файла .env
if (-not (Test-Path .env)) {
    Write-Host "Файл .env не найден. Создаем из шаблона..." -ForegroundColor Yellow
    Copy-Item dotenv.example .env
    Write-Host "Создан файл .env. Пожалуйста, отредактируйте его и добавьте ваши учетные данные Telegram." -ForegroundColor Green
    Write-Host "Затем запустите скрипт повторно." -ForegroundColor Green
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Проверяем наличие директорий
if (-not (Test-Path logs)) {
    New-Item -ItemType Directory -Path logs | Out-Null
}
if (-not (Test-Path data)) {
    New-Item -ItemType Directory -Path data | Out-Null
}

# Проверяем конфигурацию
if (-not (Test-Path config.json)) {
    Write-Host "Файл config.json не найден. Копируем docker-config.json..." -ForegroundColor Yellow
    Copy-Item docker-config.json config.json
}

# Проверяем права администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Для работы с Windows Event Logs требуются права администратора." -ForegroundColor Red
    Write-Host "Запустите PowerShell от имени администратора и повторите запуск скрипта." -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Проверяем доступ к Windows Event Logs
if (-not (Test-Path "C:\Windows\System32\winevt\Logs")) {
    Write-Host "Не удается получить доступ к директории Windows Event Logs." -ForegroundColor Red
    Write-Host "Проверьте права доступа к C:\Windows\System32\winevt\Logs" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Запускаем сборку и запуск контейнеров
Write-Host "Запуск Docker Compose..." -ForegroundColor Green
docker-compose up -d

# Проверяем статус контейнеров
Write-Host "Статус контейнеров:" -ForegroundColor Green
docker-compose ps

Write-Host ""
Write-Host "Windows Monitor Agent запущен в Docker." -ForegroundColor Green
Write-Host "Для просмотра логов используйте команду:" -ForegroundColor Cyan
Write-Host "  docker-compose logs -f windows-monitor-agent" -ForegroundColor White
Write-Host ""
Write-Host "Веб-интерфейс для просмотра логов доступен по адресу:" -ForegroundColor Cyan
Write-Host "  http://localhost:8080/" -ForegroundColor White

Read-Host "Нажмите Enter для завершения" 