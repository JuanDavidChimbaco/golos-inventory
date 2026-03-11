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

### ⚙️ Configuración MiPaquete

**Variables de entorno necesarias:**
```bash
# Proveedor activo
STORE_SHIPPING_PROVIDER=http

# API MiPaquete
STORE_SHIPPING_API_BASE_URL=https://api.mipaquete.com
STORE_SHIPPING_CREATE_PATH=/v1/shipments
STORE_SHIPPING_API_KEY=tu_api_key_aqui
STORE_SHIPPING_AUTH_HEADER=Authorization
STORE_SHIPPING_AUTH_PREFIX=Bearer

# Webhook de MiPaquete
STORE_SHIPPING_WEBHOOK_SECRET=tu_webhook_secret_para_validar_firmas

# Servicios disponibles
STORE_SHIPPING_SERVICES=eco:12000:72,standard:18000:48,express:25000:24

# Transportadora por defecto
STORE_SHIPPING_CARRIER_NAME=MiPaquete

# Timeout y validación
STORE_SHIPPING_API_TIMEOUT_SECONDS=15
STORE_SHIPPING_MAX_DELIVERY_HOURS=72
STORE_SHIPPING_AUTO_CREATE=true
STORE_SHIPPING_ENABLED=true
```

**URL del webhook:**
```
https://tu-dominio.com/api/store/shipping/webhook/
```

**Configurar en MiPaquete:**
1. URL del webhook: `https://tu-dominio.com/api/store/shipping/webhook/`
2. Eventos a notificar: `shipment.status_updated`
3. Método: `POST`
4. Headers: `Content-Type: application/json` (y opcionalmente firma HMAC)

## � Integración Completa MiPaquete

### Endpoints Disponibles

#### **Cotización de Envío**
```
POST /api/store/shipping/quote/
```
**Propósito**: Obtener costos de envío reales desde MiPaquete  
**Request:**
```json
{
  "destination": {
    "city": "Bogotá",
    "department": "Cundinamarca"
  },
  "weight_grams": 2700
}
```
**Response:**
```json
{
  "detail": "Cotización obtenida correctamente",
  "code": "STORE_SHIPPING_QUOTE_OK",
  "destination": {"city": "Bogotá", "department": "Cundinamarca"},
  "weight_grams": 2700,
  "services": [
    {
      "name": "estándar",
      "cost": "12500.00",
      "eta_hours": 48,
      "available": true,
      "currency": "COP"
    },
    {
      "name": "express",
      "cost": "18500.00",
      "eta_hours": 24,
      "available": true,
      "currency": "COP"
    }
  ]
}
```

#### **Departamentos de Colombia**
```
GET /api/store/locations/departments/
```
**Response:**
```json
{
  "detail": "Departamentos obtenidos correctamente",
  "code": "STORE_LOCATIONS_DEPARTMENTS_OK",
  "departments": [
    {"code": "antioquia", "name": "Antioquia"},
    {"code": "cundinamarca", "name": "Cundinamarca"},
    // ... todos los departamentos
  ]
}
```

#### **Ciudades por Departamento**
```
GET /api/store/locations/departments/{department_code}/cities/
```
**Ejemplo:** `GET /api/store/locations/departments/antioquia/cities/`  
**Response:**
```json
{
  "detail": "Ciudades obtenidas correctamente",
  "code": "STORE_LOCATIONS_CITIES_OK",
  "department_code": "antioquia",
  "cities": [
    {"code": "medellin", "name": "Medellín"},
    {"code": "bello", "name": "Bello"},
    // ... ciudades del departamento
  ]
}
```

#### **Puntos de Recogida**
```
GET /api/store/pickup-points/?city=bogota&department=cundinamarca
```
**Response:**
```json
{
  "detail": "Puntos de recogida obtenidos correctamente",
  "code": "STORE_PICKUP_POINTS_OK",
  "location": {"city": "bogota", "department": "cundinamarca"},
  "points": [
    {
      "id": "mp001",
      "name": "Punto MiPaquete Centro",
      "address": "Calle 1 # 2-3, Bogotá",
      "schedule": "Lunes a Viernes 8:00-18:00",
      "phone": "+57 300 123 4567",
      "coordinates": {"lat": 4.6097, "lng": -74.0817},
      "services": ["recogida", "entrega"]
    }
  ]
}
```

### Configuración Adicional

**Variables de entorno para cotización:**
```bash
# API de cotización
STORE_SHIPPING_QUOTE_API_URL=https://api.mipaquete.com/v1/quote

# Origen de envíos
STORE_SHIPPING_ORIGIN_CITY=Bogotá
STORE_SHIPPING_ORIGIN_DEPARTMENT=Cundinamarca

# Fallback local
STORE_MARGIN_SHIPPING_COST_MATRIX=local:5000:12000,regional:5000:18000,national:5000:25000
```

## 📱 Integración Frontend

### Componentes Necesarios

1. **Formulario de Dirección de Envío**
2. **Selector de Método de Envío** 
3. **Cálculo Dinámico de Costos**
4. **Puntos de Recogida**
5. **Tracking en Tiempo Real**

### Estados de Shipping

| Estado | Etiqueta | Color | Icono |
|--------|----------|-------|-------|
| `created` | "Guía creada" | 🟡 | 📦 |
| `in_transit` | "En tránsito" | 🔵 | 🚚 |
| `delivered` | "Entregado" | 🟢 | ✅ |
| `failed` | "Fallido" | 🔴 | ❌ |
| `canceled` | "Cancelado" | ⚫ | 🚫 |

## �🔧 Scripts Personalizados

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
