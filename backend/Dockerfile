FROM python:3.11-slim

# Python çıktılarını tamponlamadan (buffer) doğrudan loglara basar ve .pyc dosyalarını engeller
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Sistem bağımlılıkları (lxml ve asyncpg derlemeleri ile curl healthcheck için)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Önce sadece requirements.txt kopyalanır (Docker Layer Caching optimizasyonu)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY . .

EXPOSE 8000

# Geliştirme ortamı için hot-reload aktif başlatma komutu
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
