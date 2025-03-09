FROM python:3.10-slim

WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
# Примечание: pywin32 требует Windows, поэтому этот контейнер 
# предназначен только для сборки и тестирования на Windows-хостах
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Запускаем агент
CMD ["python", "src/main.py"] 