@echo off
setlocal

REM Проверка наличия Docker
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Docker не установлен. Установите Docker Desktop перед запуском.
    pause
    exit /b 1
)

REM Проверка запущен ли Docker
docker info >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Docker не запущен. Запустите Docker Desktop перед выполнением скрипта.
    pause
    exit /b 1
)

REM Проверяем наличие файла .env
if not exist .env (
    echo Файл .env не найден. Создаем из шаблона...
    copy dotenv.example .env
    echo Создан файл .env. Пожалуйста, отредактируйте его и добавьте ваши учетные данные Telegram.
    echo Затем запустите скрипт повторно.
    pause
    exit /b 1
)

REM Проверяем наличие директорий
if not exist logs mkdir logs
if not exist data mkdir data

REM Проверяем конфигурацию
if not exist config.json (
    echo Файл config.json не найден. Копируем docker-config.json...
    copy docker-config.json config.json
)

REM Проверяем права администратора
net session >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Для работы с Windows Event Logs требуются права администратора.
    echo Запустите скрипт от имени администратора.
    pause
    exit /b 1
)

REM Запускаем сборку и запуск контейнеров
echo Запуск Docker Compose...
docker-compose up -d

REM Проверяем статус контейнеров
echo Статус контейнеров:
docker-compose ps

echo.
echo Windows Monitor Agent запущен в Docker.
echo Для просмотра логов используйте команду:
echo   docker-compose logs -f windows-monitor-agent
echo.
echo Веб-интерфейс для просмотра логов доступен по адресу:
echo   http://localhost:8080/

pause 