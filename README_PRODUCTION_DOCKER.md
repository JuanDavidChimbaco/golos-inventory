# Golos Inventory - Despliegue con Docker

Sistema de gestión de inventario y ventas desplegado con Docker.

## 🐳 Flujo de Despliegue

### Desarrollo Local (Windows)
```powershell
# Ejecutar script de subida
.\subir.ps1
```

### Producción (Servidor)
```bash
# Ejecutar script de despliegue
./desplegar.sh
```

## 📋 Requisitos

### Entorno de Desarrollo
- Windows con PowerShell
- Docker Desktop
- Git

### Servidor de Producción
- Linux (Ubuntu/CentOS/Amazon Linux)
- Docker y Docker Compose
- Acceso SSH

## ⚙️ Configuración

### Variables de Entorno
- Copiar `config/.env.example` como `config/.env`
- Ajustar según ambiente (desarrollo/producción)
- Configurar DEBUG, ALLOWED_HOSTS, DATABASE_URL, etc.

### Grupos de Permisos
```bash
python manage.py setup_permissions --settings=config.settings_production
```

## 🔧 Scripts Personalizados

### `subir.ps1` (Windows)
Script para desarrollo local y pruebas en Optiplex.

### `desplegar.sh` (Servidor)
Script para producción en GCP.

## 📱 URLs de Verificación

- **API Docs**: `http://localhost:8000/api/docs/` (desarrollo)
- **API Docs**: `https://tu-dominio.com/api/docs/` (producción)
- **Admin**: `http://localhost:8000/admin/` o `https://tu-dominio.com/admin/`

## 🚨 Solución de Problemas

### Verificar Contenedores
```bash
docker ps
docker logs <nombre-contenedor>
```

### Rebuild en Desarrollo
```powershell
.\subir.ps1
```

### Rebuild en Producción
```bash
./desplegar.sh
```

## 📚 Documentación Adicional

- **Documentación técnica**: `config/inventory/README.md`
- **Desarrollo**: `../README.md`

---

*Despliegue simplificado con Docker* 🐳
