# Golos Inventory - Guía de Producción

**Sistema de gestión de inventario para productos y ventas**

Desarrollado por David Chimbaco

## 🚀 Despliegue en Producción

Esta guía te ayudará a desplegar Golos Inventory en un entorno de producción.

## 📋 Requisitos de Producción

- **Servidor**: Ubuntu 20.04+ / CentOS 8+ / Amazon Linux 2
- **Python**: 3.8+
- **Base de datos**: PostgreSQL 12+ (recomendado)
- **Servidor web**: Nginx
- **Servidor de aplicaciones**: Gunicorn
- **SSL/TLS**: Certificado SSL (Let's Encrypt recomendado)

## 🛠️ Configuración del Servidor

### 1. Actualizar el sistema
```bash
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# sudo yum update -y                       # CentOS/RHEL
```

### 2. Instalar dependencias
```bash
# Python y herramientas
sudo apt install python3 python3-pip python3-venv nginx postgresql postgresql-contrib -y

# Herramientas adicionales
sudo apt install build-essential libpq-dev -y
```

### 3. Configurar PostgreSQL
```bash
# Cambiar a usuario postgres
sudo -u postgres psql

# Crear base de datos y usuario
CREATE DATABASE golos_inventory;
CREATE USER golos_user WITH PASSWORD 'tu_password_seguro';
GRANT ALL PRIVILEGES ON DATABASE golos_inventory TO golos_user;
\q
```

### 4. Clonar y configurar la aplicación
```bash
# Clonar el repositorio
cd /var/www/
sudo git clone <url-del-repositorio> golos-inventory
sudo chown -R $USER:$USER /var/www/golos-inventory
cd golos-inventory

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
cd config
pip install -r ../requirements.txt
pip install gunicorn psycopg2-binary
```

### 6. Configurar variables de entorno
Copiar y configurar el archivo de entorno de producción:
```bash
cp .env.production .env
nano .env  # Editar con tus valores reales
```

**Importante:** Configura estos valores en `.env`:
- `SECRET_KEY`: Genera una nueva clave segura
- `ALLOWED_HOSTS`: Agrega tus dominios
- `DATABASE_URL`: Configura tu PostgreSQL
- `EMAIL_*`: Configura tu servicio de email

### 7. Migrar la base de datos
```bash
python manage.py migrate --settings=config.settings_production
```

### 8. Crear superusuario
```bash
python manage.py createsuperuser --settings=config.settings_production
```

### 9. Recolectar archivos estáticos
```bash
python manage.py collectstatic --settings=config.settings_production --noinput
```

## 🔧 Configuración de Gunicorn

Crear archivo de servicio Gunicorn:
```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Contenido:
```ini
[Unit]
Description=gunicorn daemon for Golos Inventory
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/golos-inventory/config
ExecStart=/var/www/golos-inventory/.venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/var/www/golos-inventory/gunicorn.sock \
    config.wsgi:application \
    --settings=config.settings_production

[Install]
WantedBy=multi-user.target
```

Iniciar y habilitar Gunicorn:
```bash
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```

## 🌐 Configuración de Nginx

Crear configuración de Nginx:
```bash
sudo nano /etc/nginx/sites-available/golos-inventory
```

Contenido:
```nginx
server {
    listen 80;
    server_name tudominio.com www.tudominio.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /var/www/golos-inventory;
    }

    location /media/ {
        root /var/www/golos-inventory;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/golos-inventory/gunicorn.sock;
    }
}
```

Activar el sitio:
```bash
sudo ln -s /etc/nginx/sites-available/golos-inventory /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## 🔒 Configuración SSL con Let's Encrypt

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtener certificado
sudo certbot --nginx -d tudominio.com -d www.tudominio.com

# Configurar renovación automática
sudo crontab -e
# Agregar: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🔧 Configuración Adicional para Producción

### Actualizar settings.py para producción
Asegúrate de tener estas configuraciones en `config/config/settings.py`:

```python
# Seguridad
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_FRAME_DENY = True
X_FRAME_OPTIONS = 'DENY'

# Sesiones
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Base de datos PostgreSQL
import dj_database_url

DATABASES = {
    'default': dj_database_url.parse(os.getenv('DATABASE_URL'))
}
```

### Instalar dependencias adicionales
```bash
pip install dj-database-url
```

## 📊 Monitoreo y Logs

### Ver logs de Gunicorn
```bash
sudo journalctl -u gunicorn
```

### Ver logs de Nginx
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Reiniciar servicios
```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

## 🔄 Actualizaciones

### Para actualizar la aplicación en producción:

```bash
cd /var/www/golos-inventory
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
cd config
python manage.py migrate --settings=config.settings_production
python manage.py collectstatic --settings=config.settings_production --noinput
sudo systemctl restart gunicorn
```

## 🚨 Seguridad Adicional

### Configurar firewall
```bash
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### Backup de la base de datos
```bash
# Crear script de backup
sudo nano /usr/local/bin/backup_golos.sh
```

Contenido del script:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/golos-inventory"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

pg_dump -h localhost -U golos_user golos_inventory > $BACKUP_DIR/backup_$DATE.sql
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

Hacer ejecutable y programar:
```bash
sudo chmod +x /usr/local/bin/backup_golos.sh
sudo crontab -e
# Agregar: 0 2 * * * /usr/local/bin/backup_golos.sh
```

## 📈 Rendimiento

### Optimización adicional
- Configurar Redis para caché
- Usar CDN para archivos estáticos
- Configurar balanceador de carga si es necesario
- Monitorear con herramientas como New Relic o DataDog

## 🆘 Troubleshooting

### Problemas comunes:
1. **Error 502 Bad Gateway**: Gunicorn no está corriendo
2. **Error 504 Gateway Timeout**: Timeout de la aplicación
3. **Static files not found**: Revisar configuración de Nginx
4. **Database connection failed**: Verificar credenciales de PostgreSQL

### Comandos útiles:
```bash
# Verificar estado de servicios
sudo systemctl status gunicorn nginx

# Verificar conexiones a la base de datos
sudo -u postgres psql -c "\l"

# Probar configuración de Nginx
sudo nginx -t
```

## 👨‍💻 Soporte

**David Chimbaco**
- Desarrollador de Software
- Creador de Golos Inventory

Para soporte técnico, abre un issue en el repositorio del proyecto.

---

*Esta guía está diseñada para despliegues en producción. Asegúrate de probar en un entorno de staging antes de aplicar en producción.*
