# Golos Inventory - Guía de Producción

**Sistema de gestión de inventario y ventas con Django Permissions y arquitectura modular**

Desarrollado por David Chimbaco

---

## 🎯 **Visión General**

Esta guía te ayudará a desplegar Golos Inventory en un entorno de producción con la arquitectura actualizada, permisos granulares y scripts organizados.

---

## 📋 **Requisitos de Producción**

### **🖥️ Servidor:**
- **Ubuntu 20.04+** / **CentOS 8+** / **Amazon Linux 2**
- **Mínimo**: 2 CPU, 4GB RAM, 20GB SSD
- **Recomendado**: 4 CPU, 8GB RAM, 50GB SSD

### **🐍 Software:**
- **Python**: 3.8+
- **Base de datos**: PostgreSQL 12+ (recomendado)
- **Servidor web**: Nginx 1.18+
- **Servidor de aplicaciones**: Gunicorn 20+
- **SSL/TLS**: Certificado SSL (Let's Encrypt recomendado)

### **� Herramientas:**
- **Git** para control de versiones
- **Docker** (opcional para contenerización)
- **Redis** (opcional para caching)

---

## �🛠️ **Configuración del Servidor**

### **1. Actualizar el sistema**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
sudo yum upgrade -y
```

### **2. Instalar dependencias**
```bash
# Python y herramientas
sudo apt install python3 python3-pip python3-venv python3-dev build-essential libpq-dev

# PostgreSQL
sudo apt install postgresql postgresql-contrib

# Nginx
sudo apt install nginx

# Git
sudo apt install git
```

### **3. Crear usuario de aplicación**
```bash
sudo adduser golos
sudo usermod -aG sudo golos
sudo su - golos
```

---

## 📁 **Estructura del Proyecto en Producción**

### **🗂️ Directorios Recomendados:**
```
/home/golos/
├── 📁 golos-inventory/          # Código fuente
├── 📁 .venv/                   # Entorno virtual
├── 📁 logs/                    # Logs de aplicación
├── 📁 media/                   # Archivos multimedia
├── 📁 static/                  # Archivos estáticos
└── 📁 backups/                 # Backups de BD
```

### **🔧 Configuración de Permisos:**
```bash
# Asegurar permisos correctos
chmod 755 /home/golos/golos-inventory
chmod +x /home/golos/golos-inventory/manage.py
```

---

## 🐘 **Configuración de Base de Datos**

### **1. Instalar y configurar PostgreSQL**
```bash
# Instalar PostgreSQL
sudo apt install postgresql postgresql-contrib

# Iniciar servicio
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Crear base de datos y usuario
sudo -u postgres psql
CREATE DATABASE golos_inventory;
CREATE USER golos_user WITH PASSWORD 'contraseña_segura';
GRANT ALL PRIVILEGES ON DATABASE golos_inventory TO golos_user;
\q
```

### **2. Configurar PostgreSQL**
```bash
# Editar configuración
sudo nano /etc/postgresql/12/main/postgresql.conf

# Ajustar configuración
listen_addresses = 'localhost'
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB

# Reiniciar PostgreSQL
sudo systemctl restart postgresql
```

---

## 🚀 **Configuración de la Aplicación**

### **1. Clonar y configurar**
```bash
# Clonar repositorio
cd /home/golos
git clone https://github.com/JuanDavidChimbaco/golos-inventory.git
cd golos-inventory

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### **2. Configurar variables de entorno**
```bash
# Crear archivo de entorno para producción
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Crear .env.production con clave generada
echo "SECRET_KEY='tu-clave-generada-aqui'" > .env.production
echo "DEBUG=False" >> .env.production
echo "ALLOWED_HOSTS=tudominio.com,www.tudominio.com" >> .env.production
echo "DATABASE_URL=postgresql://golos_user:contraseña_segura@localhost:5432/golos_inventory" >> .env.production

# Editar archivo con tus datos reales
nano .env.production
```

**Variables esenciales:**
```bash
# Seguridad
SECRET_KEY='tu_clave_secreta_muy_larga_y_aleatoria'
DEBUG=False
ALLOWED_HOSTS=['tudominio.com', 'www.tudominio.com']

# Base de datos
DATABASE_URL=postgresql://golos_user:contraseña_segura@localhost:5432/golos_inventory

# Estático y media
STATIC_URL=/static/
STATIC_ROOT=/home/golos/golos-inventory/static/
MEDIA_URL=/media/
MEDIA_ROOT=/home/golos/golos-inventory/media/

# Email (opcional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email@gmail.com
EMAIL_HOST_PASSWORD=tu_contraseña_app
```

### **3. Aplicar migraciones y configurar permisos**
```bash
cd config
python manage.py migrate

# Configurar permisos y grupos
python manage.py shell < inventory/scripts/setup_permissions.py

# Crear superusuario
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

---

## 🌐 **Configuración de Nginx**

### **1. Crear configuración de Nginx**
```bash
sudo nano /etc/nginx/sites-available/golos-inventory
```

**Configuración completa:**
```nginx
server {
    listen 80;
    server_name tudominio.com www.tudominio.com;
    return 301 https://$server_name$request_uri;

    server {
        listen 443 ssl http2;
        server_name tudominio.com www.tudominio.com;

        # SSL
        ssl_certificate /etc/letsencrypt/live/tudominio.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/tudominio.com/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # Seguridad
        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-Content-Type-Options "nosniff";
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Archivos estáticos
        location /static/ {
            alias /home/golos/golos-inventory/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        location /media/ {
            alias /home/golos/golos-inventory/media/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Aplicación
        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # API Documentation
        location /api/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### **2. Activar configuración**
```bash
sudo ln -s /etc/nginx/sites-available/golos-inventory /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🐧 **Configuración de Gunicorn**

### **1. Crear archivo de servicio Gunicorn**
```bash
nano /etc/systemd/system/golos-inventory.service
```

```ini
[Unit]
Description=Gunicorn instance for Golos Inventory
After=network.target

[Service]
User=golos
Group=golos
WorkingDirectory=/home/golos/golos-inventory
Environment=PATH=/home/golos/golos-inventory/.venv/bin
ExecStart=/home/golos/golos-inventory/.venv/bin/gunicorn \
    --workers 3 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 30 \
    --keep-alive 5 \
    --bind unix:/run/golos-inventory.sock \
    config.wsgi:application

[Install]
WantedBy=multi-user.target
```

### **2. Activar y iniciar servicio**
```bash
sudo systemctl daemon-reload
sudo systemctl enable golos-inventory.service
sudo systemctl start golos-inventory.service
```

---

## � **Configuración SSL con Let's Encrypt**

### **1. Instalar Certbot**
```bash
sudo apt install certbot python3-certbot-nginx
```

### **2. Obtener certificado**
```bash
sudo certbot --nginx -d tudominio.com -d www.tudominio.com
```

### **3. Renovación automática**
```bash
sudo crontab -e
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## � **Configuración de Monitoreo**

### **1. Logs de la aplicación**
```bash
# Configurar logging en settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process} {thread} {message}',
        },
        'file': {
            'format': '{levelname} {asctime} {module} {process} {thread} {message}',
            'filename': '/home/golos/golos-inventory/logs/django.log',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/home/golos/golos-inventory/logs/django.log',
            'formatter': 'file',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
```

### **2. Logs de Nginx**
```bash
# Configurar logrotate
sudo nano /etc/logrotate.d/golos-inventory
```

```nginx
/home/golos/golos-inventory/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 golos golos www-data
    postrotate
        systemctl reload nginx
}
```

---

## � **Proceso de Despliegue**

### **1. Preparación del entorno**
```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Crear usuario
sudo adduser golos
sudo usermod -aG sudo golos
```

### **2. Configuración de base de datos**
```bash
# Instalar PostgreSQL
sudo apt install postgresql postgresql-contrib

# Crear base de datos
sudo -u postgres createdb golos_inventory
sudo -u postgres createuser golos_user
sudo -u postgres psql -c "ALTER USER golos_user WITH PASSWORD 'contraseña_segura';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE golos_inventory TO golos_user;"
```

### **3. Despliegue de la aplicación**
```bash
# Clonar y configurar
git clone https://github.com/JuanDavidChimbaco/golos-inventory.git
cd golos-inventory
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configurar variables
# Crear archivo de entorno para producción
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Crear .env.production con clave generada
echo "SECRET_KEY='tu-clave-generada-aqui'" > .env.production
echo "DEBUG=False" >> .env.production
echo "ALLOWED_HOSTS=tudominio.com,www.tudominio.com" >> .env.production
echo "DATABASE_URL=postgresql://golos_user:contraseña_segura@localhost:5432/golos_inventory" >> .env.production

# Editar .env.production con datos reales

# Migrar y configurar
cd config
python manage.py migrate
python manage.py shell < inventory/scripts/setup_permissions.py
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### **4. Configuración de servicios**
```bash
# Configurar Nginx
sudo nano /etc/nginx/sites-available/golos-inventory
sudo ln -s /etc/nginx/sites-available/golos-inventory /etc/nginx/sites-enabled/
sudo nginx -t

# Configurar Gunicorn
sudo nano /etc/systemd/system/golos-inventory.service
sudo systemctl daemon-reload
sudo systemctl enable golos-inventory.service
sudo systemctl start golos-inventory.service

# Configurar SSL
sudo certbot --nginx -d tudominio.com -d www.tudominio.com
```

### **5. Verificación final**
```bash
# Verificar servicios
sudo systemctl status nginx
sudo systemctl status golos-inventory
sudo systemctl status postgresql

# Verificar aplicación
curl -I http://localhost:8000/api/docs/
curl -I https://tudominio.com/api/docs/
```

---

## 🔧 **Scripts de Mantenimiento**

### **1. Backup de base de datos**
```bash
#!/bin/bash
# backup_db.sh
BACKUP_DIR="/home/golos/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/golos_inventory_$DATE.sql"

mkdir -p $BACKUP_DIR
pg_dump -h localhost -U golos_user -d golos_inventory > $BACKUP_FILE

echo "Backup completado: $BACKUP_FILE"
```

### **2. Actualización de la aplicación**
```bash
#!/bin/bash
# update_app.sh
cd /home/golos/golos-inventory
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
cd config
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart golos-inventory
```

### **3. Verificación de permisos**
```bash
#!/bin/bash
# check_permissions.sh
cd /home/golos/golos-inventory
source .venv/bin/activate
cd config
python manage.py shell < inventory/scripts/setup_permissions.py
```

---

## 🚨 **Configuración de Seguridad**

### **1. Firewall**
```bash
# Configurar UFW
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw allow 8000
sudo ufw allow 5432
sudo ufw enable
```

### **2. Seguridad de archivos**
```bash
# Permisos de archivos
chmod 750 /home/golos/golos-inventory
chmod 640 /home/golos/golos-inventory/logs
chmod 640 /home/golos/golos-inventory/media
chmod 640 /home/golos/golos-inventory/static
```

### **3. Configuración de Django**
```bash
# settings.py de producción
DEBUG=False
ALLOWED_HOSTS=['tudominio.com', 'www.tudominio.com']
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_BROWSER_XSS_PROTECTION=True
SECURE_CONTENT_TYPE_NOSNIFF=True
```

---

## 📈 **Monitoreo y Logging**

### **1. Logs importantes**
```bash
# Logs de Django
tail -f /home/golos/golos-inventory/logs/django.log

# Logs de Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Logs de PostgreSQL
sudo tail -f /var/log/postgresql/postgresql.log
```

### **2. Métricas de rendimiento**
```bash
# Uso de recursos
htop -p golos

# Conexiones de base de datos
psql -U golos_user -d golos_inventory -c "SELECT count(*) FROM auth_user;"

# Espacio en disco
df -h /home/golos/golos-inventory
```

---

## 🚨 **Solución de Problemas Comunes**

### **❌ Error 502 Bad Gateway**
```bash
# Verificar Gunicorn
sudo systemctl status golos-inventory

# Verificar socket
ls -la /run/golos-inventory.sock

# Reiniciar servicios
sudo systemctl restart golos-inventory
sudo systemctl restart nginx
```

### **❌ Error de base de datos**
```bash
# Verificar conexión
psql -U golos_user -h localhost -d golos_inventory

# Verificar logs de PostgreSQL
sudo tail -f /var/log/postgresql/postgresql.log
```

### **❌ Error de permisos**
```bash
# Verificar permisos de archivos
ls -la /home/golos/golos-inventory/media
ls -la /home/golos/golos-inventory/static

# Ejecutar script de permisos
cd /home/golos/golos-inventory
python manage.py shell < inventory/scripts/setup_permissions.py
```

---

## 📞 **Soporte y Monitoreo**

### **📧 Scripts de mantenimiento**
- **backup_db.sh** - Backup automático de base de datos
- **update_app.sh** - Actualización de la aplicación
- **check_permissions.sh** - Verificación de permisos

### **� Monitoreo recomendado**
- **Prometheus + Grafana** para métricas
- **Sentry** para error tracking
- **Uptime Robot** para disponibilidad

---

## 🎯 **Verificación Final**

### **✅ Checklist de despliegue:**
- [ ] Servidor actualizado y seguro
- [ ] PostgreSQL configurado y funcionando
- [ ] Aplicación desplegada y funcionando
- [ ] Nginx configurado y sirviendo HTTPS
- [ ] SSL/TLS configurado y válido
- [ ] Permisos configurados correctamente
- [ ] Logs configurados y rotando
- [ ] Scripts de mantenimiento listos
- [ ] Monitoreo básico configurado

### **🔗 URLs de verificación:**
- **API**: https://tudominio.com/api/docs/
- **Admin**: https://tudominio.com/admin/
- **Health Check**: https://tudominio.com/api/health/

---

## 📚 **Documentación Adicional**

- **📖 Documentación técnica**: `config/inventory/README.md`
- **📋 Arquitectura**: `config/inventory/docs/ARCHITECTURE.md`
- **🛠️ Scripts**: `config/inventory/scripts/README.md`
- **⚙️ Configuración de entorno**: `../README.md#configuración-de-entorno`

---

*Esta guía mantiene el sistema seguro, escalable y bien documentado para producción* 🚀.*
