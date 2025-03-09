@echo off
echo Запуск агента мониторинга...

REM Проверяем наличие файла .env в корне проекта
if not exist ..\\.env (
    echo Ошибка: Файл .env не найден в корне проекта.
    echo Создайте файл .env на основе .env.example.
    pause
    exit /b 1
)

REM Создаем директорию для логов, если она не существует
if not exist logs mkdir logs

REM Проверяем наличие Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Ошибка: Python не найден. Пожалуйста, установите Python 3.8 или выше.
    pause
    exit /b 1
)

REM Проверяем наличие файла requirements.txt
if not exist requirements.txt (
    echo Ошибка: Файл requirements.txt не найден.
    pause
    exit /b 1
)

REM Устанавливаем зависимости, если они еще не установлены
echo Установка зависимостей...
pip install -r requirements.txt

REM Копируем файл .env в текущую директорию для удобства
copy ..\\.env .env >nul

REM Запускаем агент
echo Запуск агента...
python src\main.py

pause 