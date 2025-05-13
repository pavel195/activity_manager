FROM python:3.10-slim

WORKDIR /app

# Установка необходимых системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей проекта
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Установка дополнительных зависимостей для Windows-специфичных библиотек
RUN pip install --no-cache-dir python-dotenv fpdf2 schedule

# Копирование исходного кода
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config.json .
COPY sysmon_config.xml .
COPY dotenv.example .
COPY wma.py .
COPY docker_entrypoint.py .

# Создание директорий для данных и логов
RUN mkdir -p logs data

# Назначаем права на выполнение docker_entrypoint.py
RUN chmod +x docker_entrypoint.py

# Создаем пользователя с ограниченными правами
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app

# Переключение на пользователя с ограниченными правами
USER appuser

# Установка команды для запуска через точку входа
ENTRYPOINT ["python", "docker_entrypoint.py"] 