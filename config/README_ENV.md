# Configuración de Variables de Entorno

Este proyecto utiliza variables de entorno para configurar diferentes ambientes.

## Archivos de Configuración

### Desarrollo Local
1. Copia el archivo de ejemplo:
   ```bash
   cp .env.local.example .env.local
   ```

2. Edita `.env.local` con tus datos de desarrollo

### Producción
1. Copia el archivo de ejemplo:
   ```bash
   cp .env.production.example .env.production
   ```

2. Edita `.env.production` con tus datos de producción

## Variables Requeridas

### Mínimas para funcionamiento:
- `SECRET_KEY`: Clave secreta de Django
- `DEBUG`: True/False
- `ALLOWED_HOSTS`: Lista de dominios permitidos

### Base de Datos (producción):
- `DB_NAME`: Nombre de la base de datos
- `DB_USER`: Usuario de la base de datos
- `DB_PASSWORD`: Contraseña de la base de datos
- `DB_HOST`: Host de la base de datos
- `DB_PORT`: Puerto de la base de datos

### CORS:
- `CORS_ALLOWED_ORIGINS`: Dominios permitidos para API

## Seguridad

⚠️ **IMPORTANTE**: Nunca subas archivos `.env` reales al repositorio. Solo los archivos `.example` deben estar en el control de versiones.
