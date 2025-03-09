.PHONY: help server agent stop logs clean setup-dirs setup-server setup-agent setup-env

# Переменные
DOCKER_COMPOSE = docker-compose
PYTHON = python
PIP = pip

# Цвета для вывода
GREEN = \033[0;32m
RED = \033[0;31m
YELLOW = \033[0;33m
NC = \033[0m # No Color

# Помощь
help:
	@echo "$(GREEN)Система мониторинга процессов Windows$(NC)"
	@echo ""
	@echo "$(YELLOW)Доступные команды:$(NC)"
	@echo "  $(GREEN)make setup-env$(NC)     - Создать файл .env из шаблона"
	@echo "  $(GREEN)make setup-dirs$(NC)    - Создать необходимые директории"
	@echo "  $(GREEN)make setup-server$(NC)  - Подготовить серверную часть"
	@echo "  $(GREEN)make setup-agent$(NC)   - Подготовить агент для Windows"
	@echo "  $(GREEN)make server$(NC)        - Запустить серверную часть (PostgreSQL, Elasticsearch, Kibana, API)"
	@echo "  $(GREEN)make agent$(NC)         - Запустить агент (только для Windows)"
	@echo "  $(GREEN)make logs$(NC)          - Показать логи сервера"
	@echo "  $(GREEN)make stop$(NC)          - Остановить все контейнеры"
	@echo "  $(GREEN)make clean$(NC)         - Остановить и удалить все контейнеры и тома"
	@echo ""
	@echo "$(YELLOW)Доступ к компонентам:$(NC)"
	@echo "  $(GREEN)API сервера:$(NC)       http://localhost:8000"
	@echo "  $(GREEN)Kibana:$(NC)            http://localhost:5601"
	@echo "  $(GREEN)Elasticsearch:$(NC)     http://localhost:9200"

# Создание файла .env из шаблона
setup-env:
	@echo "$(GREEN)Проверка наличия файла .env...$(NC)"
	@if [ ! -f ".env" ]; then \
		echo "$(YELLOW)Файл .env не найден. Создаем из шаблона...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN)Файл .env создан. Пожалуйста, отредактируйте его с вашими настройками.$(NC)"; \
	else \
		echo "$(GREEN)Файл .env уже существует.$(NC)"; \
	fi

# Создание необходимых директорий
setup-dirs:
	@echo "$(GREEN)Создание необходимых директорий...$(NC)"
	@mkdir -p server/logs
	@mkdir -p agent/logs
	@echo "$(GREEN)Директории созданы.$(NC)"

# Подготовка серверной части
setup-server: setup-env setup-dirs
	@echo "$(GREEN)Подготовка серверной части...$(NC)"
	@if [ ! -d "server" ]; then \
		echo "$(RED)Ошибка: Директория server не найдена.$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Серверная часть готова к запуску.$(NC)"

# Подготовка агента
setup-agent: setup-env setup-dirs
	@echo "$(GREEN)Подготовка агента для Windows...$(NC)"
	@if [ ! -d "agent" ]; then \
		echo "$(RED)Ошибка: Директория agent не найдена.$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Агент готов к запуску на Windows-машине.$(NC)"
	@echo "$(YELLOW)Для запуска агента на Windows используйте:$(NC)"
	@echo "  cd agent && start_agent.bat"

# Запуск серверной части
server: setup-server
	@echo "$(GREEN)Запуск серверной части...$(NC)"
	@$(DOCKER_COMPOSE) up -d postgres elasticsearch kibana server
	@echo "$(GREEN)Проверка статуса контейнеров...$(NC)"
	@$(DOCKER_COMPOSE) ps
	@echo "$(GREEN)Серверная часть запущена.$(NC)"

# Запуск агента (только для Windows)
agent:
	@echo "$(YELLOW)Эта команда предназначена только для Windows.$(NC)"
	@echo "$(YELLOW)Для запуска агента на Windows используйте:$(NC)"
	@echo "  cd agent && start_agent.bat"

# Просмотр логов сервера
logs:
	@echo "$(GREEN)Просмотр логов сервера...$(NC)"
	@$(DOCKER_COMPOSE) logs -f server

# Остановка всех контейнеров
stop:
	@echo "$(GREEN)Остановка всех контейнеров...$(NC)"
	@$(DOCKER_COMPOSE) stop
	@echo "$(GREEN)Все контейнеры остановлены.$(NC)"

# Полная очистка (остановка и удаление контейнеров и томов)
clean:
	@echo "$(RED)Внимание! Эта команда удалит все контейнеры и данные.$(NC)"
	@read -p "Вы уверены? [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		echo "$(GREEN)Остановка и удаление всех контейнеров и томов...$(NC)"; \
		$(DOCKER_COMPOSE) down -v; \
		echo "$(GREEN)Все контейнеры и тома удалены.$(NC)"; \
	else \
		echo "$(GREEN)Операция отменена.$(NC)"; \
	fi 