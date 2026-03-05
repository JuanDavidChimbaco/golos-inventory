# Usamos Python 3.12 (una versión más moderna que la de tu Debian)
FROM python:3.12-slim

# Variables de entorno para optimizar Python en Docker
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos dependencias del sistema necesarias para psycopg2 y Pillow
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalamos las dependencias de Python
# Copiamos ambos archivos como mencionaste
COPY requirements.txt .
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copiamos el código de tu proyecto
COPY . .

# Exponemos el puerto donde correrá Gunicorn
EXPOSE 8000

# Comando para iniciar Gunicorn (Ajusta 'config.wsgi' si tu carpeta principal se llama distinto)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]