FROM python:3.12-slim

# Evita archivos .pyc y asegura logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Forzamos el uso de la configuración de producción
ENV DJANGO_SETTINGS_MODULE=config.settings_production

WORKDIR /app

# Instalamos solo lo necesario y LIMPIAMOS después
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    && pip install --no-cache-dir gunicorn whitenoise \
    && apt-get purge -y --auto-remove gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .
# Recolecta archivos estáticos sin preguntar
RUN python config/manage.py collectstatic --noinput --settings=config.settings_production

# Comando final optimizado
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--pythonpath", "config", "config.wsgi:application"]