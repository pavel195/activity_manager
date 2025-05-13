# Windows Monitor Agent - WSL версия

Это руководство описывает процесс установки и запуска Windows Monitor Agent в среде Windows Subsystem for Linux (WSL).

## Преимущества запуска в WSL

- Возможность использования Linux-контейнеров Docker для мониторинга Windows
- Лучшая производительность по сравнению с Docker Desktop на Windows
- Упрощенное управление контейнерами и логами
- Доступ ко всем функциям мониторинга Windows Event Logs

## Предварительные требования

1. Windows 10 или Windows 11 с установленным WSL 2
2. Ubuntu 20.04 LTS или более новая версия в WSL
3. Docker установленный в WSL
4. Права администратора в Windows (требуется для доступа к Windows Event Logs)

## Установка WSL 2

Если у вас еще не установлен WSL 2, следуйте этим инструкциям:

1. Откройте PowerShell от имени администратора и выполните:

```powershell
wsl --install
```

2. Перезагрузите компьютер
3. Откройте Microsoft Store и установите Ubuntu
4. Запустите Ubuntu и создайте пользователя

## Установка Docker в WSL

1. Откройте терминал Ubuntu в WSL и выполните:

```bash
# Обновляем пакеты
sudo apt-get update

# Устанавливаем необходимые зависимости
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Добавляем официальный GPG-ключ Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Настраиваем репозиторий Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Обновляем список пакетов
sudo apt-get update

# Устанавливаем Docker Engine и Docker Compose
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-compose

# Добавляем текущего пользователя в группу docker
sudo usermod -aG docker $USER

# Запускаем Docker
sudo service docker start
```

2. Выйдите из WSL и войдите снова, чтобы применить изменения группы

## Установка и запуск Windows Monitor Agent

### Вариант 1: Запуск из PowerShell (Windows)

1. Скачайте или клонируйте репозиторий Windows Monitor Agent
2. Откройте PowerShell от имени администратора
3. Перейдите в директорию с проектом
4. Запустите скрипт `wsl-start.ps1`:

```powershell
.\wsl-start.ps1
```

### Вариант 2: Запуск напрямую из WSL

1. Откройте терминал Ubuntu в WSL
2. Перейдите в директорию с проектом (используйте путь WSL)
3. Убедитесь, что скрипт `wsl-start.sh` имеет права на выполнение:

```bash
chmod +x wsl-start.sh
```

4. Запустите скрипт:

```bash
./wsl-start.sh
```

## Настройка

При первом запуске будут созданы следующие файлы:

- `.env` - файл с переменными окружения для Telegram и других сервисов
- `config.json` - файл конфигурации агента
- `docker-compose.wsl.yml` - файл Docker Compose, адаптированный для WSL

Отредактируйте файл `.env` и добавьте свой Telegram токен и Chat ID:

```
TELEGRAM_TOKEN=your_telegram_bot_token
CHAT_ID=your_chat_id
VT_API_KEY=your_virustotal_api_key
```

## Управление агентом

### Просмотр логов

```bash
docker-compose -f docker-compose.wsl.yml logs -f windows-monitor-agent
```

### Остановка агента

```bash
docker-compose -f docker-compose.wsl.yml down
```

### Перезапуск агента

```bash
docker-compose -f docker-compose.wsl.yml restart windows-monitor-agent
```

## Веб-интерфейс для просмотра логов

Веб-интерфейс доступен по адресу: http://localhost:8080/

## Особенности WSL-версии

1. Windows Event Logs монтируются из Windows в контейнер через WSL
2. Для корректной работы требуются права администратора в Windows
3. Путь к Windows Event Logs настроен автоматически

## Устранение неполадок

### Проблема с доступом к Windows Event Logs

Если в логах появляется сообщение о невозможности доступа к логам Windows, убедитесь, что:

1. PowerShell запущен от имени администратора
2. Путь к логам Windows корректно смонтирован в WSL

### Проблема с Docker в WSL

Если Docker не запускается, выполните:

```bash
sudo service docker start
```

### Проблема с правами доступа к файлам в WSL

Если возникают проблемы с правами доступа, выполните:

```bash
chmod -R 755 .
```

## Советы по использованию

1. Для автоматического запуска при старте Windows добавьте скрипт `wsl-start.ps1` в автозагрузку
2. Для мониторинга нескольких систем используйте разные Telegram чаты
3. Настройте список разрешенных процессов и служб в файле `config.json` 