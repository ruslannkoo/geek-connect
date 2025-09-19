# Використовуємо офіційний Python 3.11 (бо там є audioop)
FROM python:3.11-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо залежності
COPY requirements.txt .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код бота
COPY . .

# Запускаємо бота
CMD ["python", "main.py"]
