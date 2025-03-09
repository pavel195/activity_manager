FROM python:3.10-slim

WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем пользователя без прав root
RUN useradd -m appuser
USER appuser

# Запускаем сервер
CMD ["python", "src/main.py"] 