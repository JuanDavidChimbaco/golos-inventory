# Golos Inventory - Sistema de Gestión con Django Permissions

**Sistema de gestión de inventario y ventas con API REST y permisos granulares**

Desarrollado por David Chimbaco

---

## Visión General

Golos Inventory es un sistema completo de gestión de inventario y ventas con arquitectura modular, permisos granulares y listo para integración con plataformas e-commerce.

### Características Principales
- Django Permissions: Sistema de permisos nativo y escalable
- Arquitectura Modular: Código organizado por funcionalidad
- API RESTful: 40 endpoints con Swagger/ReDoc
- Multi-rol: Usuarios pueden pertenecer a múltiples grupos
- E-Commerce Ready: Integración con tiendas online
- Control de Stock: Validaciones en tiempo real
- Gestión de Imágenes: Optimización automática
- Auditoría Completa: Registro de todas las acciones

---

## Inicio Rápido

### 1. Clonar y Configurar
```bash
git clone https://github.com/JuanDavidChimbaco/golos-inventory.git
cd golos-inventory
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### **2. Configurar Variables de Entorno**
```bash
# Crear archivo de entorno para desarrollo
echo "SECRET_KEY='django-insecure-dev-key-for-local-testing'" > .env.local
echo "DEBUG=True" >> .env.local
echo "ALLOWED_HOSTS=localhost,127.0.0.1" >> .env.local
```

### **3. Configurar Permisos y Grupos**
```bash
cd config
python manage.py shell < inventory/scripts/setup_permissions.py
```

### **4. Iniciar Servidor**
```bash
python manage.py runserver
```

### **5. Acceder a la API**
- Swagger UI: http://127.0.0.1:8000/api/docs/
- ReDoc: http://127.0.0.1:8000/api/redoc/
- Admin Django: http://127.0.0.1:8000/admin/

---

## ⚙️ **Configuración de Entorno**

### **🔧 Variables Esenciales**

#### **📦 Desarrollo (.env.local):**
```bash
# Crear archivo de entorno para desarrollo
SECRET_KEY='django-insecure-dev-key-for-local-testing'
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

#### **🚀 Producción (.env.production):**
```bash
# Variables críticas para producción
SECRET_KEY='generar-clave-segura-para-produccion'
DEBUG=False
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
DATABASE_URL=postgresql://user:password@localhost:5432/golos_inventory
```

### **🛠️ Configuración Rápida**

#### **🔧 Desarrollo:**
```bash
# Crear archivo automáticamente
echo "SECRET_KEY='django-insecure-dev-key-for-local-testing'" > .env.local
echo "DEBUG=True" >> .env.local
echo "ALLOWED_HOSTS=localhost,127.0.0.1" >> .env.local
```

#### **🚀 Producción:**
```bash
# Generar clave segura
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Crear archivo de producción
echo "SECRET_KEY='tu-clave-generada'" > .env.production
echo "DEBUG=False" >> .env.production
echo "ALLOWED_HOSTS=tudominio.com,www.tudominio.com" >> .env.production
```

### **📋 Variables Disponibles**

| Variable | Desarrollo | Producción | Descripción |
|----------|-------------|------------|-------------|
| `SECRET_KEY` | Clave de desarrollo | Clave segura | Clave secreta de Django |
| `DEBUG` | `True` | `False` | Modo debug |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `tudominio.com` | Hosts permitidos |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | PostgreSQL | URL de base de datos |

### **🔐 Seguridad**

#### **🚨 Nunca commitear archivos .env:**
```bash
# .gitignore
.env.local
.env.production
.env.*
```

#### **🔑 Generar SECRET_KEY segura:**
```bash
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🔐 **Sistema de Permisos**

### Grupos de Usuarios Configurados:

| Grupo | Permisos | Funcionalidad |
|-------|----------|---------------|
| Customers | 3 permisos | Clientes e-commerce |
| Sales | 5 permisos | Equipo de ventas |
| Inventory | 7 permisos | Bodegueros |
| Managers | 20 permisos | Administradores |

### Permisos Clave:
- inventory.confirm_sale - Confirmar ventas
- inventory.manage_inventory - Gestionar inventario
- auth.add_user - Crear usuarios (solo Managers)

---

## Integración E-Commerce

### Flujo de Cliente:
```python
# 1. Cliente se registra automáticamente en grupo Customers
from inventory.scripts.ecommerce_integration import ECommerceCustomer

customer = ECommerceCustomer.create_customer(
    username="cliente123",
    email="cliente@tienda.com",
    password="segura123"
)

# 2. Cliente crea pedido (API REST)
POST /api/sales/
{
    "customer": "Juan Pérez",
    "details": [{"variant": 1, "quantity": 2, "unit_price": 10.50}]
}

# 3. Pedido queda en "pending" → Equipo Sales confirma
POST /api/sales/{id}/confirm/
```

---

## Estructura del Proyecto

```
golos-inventory/ 
├── README.md                    # Este archivo - Overview general
├── README_PRODUCTION.md        # Guía de producción
├── README_ENV.md                # Variables de entorno
├── requirements.txt             # Dependencias Python
├── .gitignore                   # Archivos ignorados
├── .venv/                       # Entorno virtual
└── config/                      # Configuración Django
    ├── settings.py               # Configuración Django
    ├── urls.py                   # URLs principales
    ├── wsgi.py                   # WSGI para producción
    └── inventory/                 # Ap principal
        ├── README.md            # Documentación técnica detallada
        ├── models.py            # Modelos con permisos
        ├── docs/                # Documentación API
        ├── users/               # Gestión de usuarios
        ├── sales/               # Gestión de ventas
        ├── products/           # Catálogo de productos
        ├── inventory_management/ # Control de stock
        ├── core/                # Funcionalidades compartidas
        ├── scripts/             # Scripts de utilidad
        └── [archivos Django]      # Configuración estándar
```

---

## Documentación Detallada

### Documentación Técnica:
- `config/inventory/README.md` - Documentación completa del sistema
- `config/inventory/docs/ARCHITECTURE.md` - Arquitectura detallada
- `config/inventory/scripts/README.md` - Guía de scripts

### Despliegue:
- `README_PRODUCTION.md` - Guía completa de producción
- `README_ENV.md` - Variables de entorno

### Scripts y Utilidades:
- `scripts/setup_permissions.py` - Configuración inicial de permisos
- `scripts/user_management.py` - Gestión de usuarios
- `scripts/ecommerce_integration.py` - Integración e-commerce

---

## Requisitos

### Mínimos:
- Python 3.8+
- pip
- Git

### Para Desarrollo:
- Django 4.2+
- Django REST Framework
- Django Simple JWT
- DRF Spectacular

### Para Producción:
- PostgreSQL 12+ (recomendado)
- Nginx
- Gunicorn
- SSL/TLS

---

## Scripts Útiles

### Configuración Inicial:
```bash
python manage.py shell < config/inventory/scripts/setup_permissions.py
```

### Gestión de Usuarios:
```python
from inventory.scripts import assign_user_to_groups
assign_user_to_groups("juan", ["Sales", "Inventory"])
```

### Integración E-Commerce:
```python
from inventory.scripts import ECommerceCustomer
customer = ECommerceCustomer.create_customer("cliente1", "email@tienda.com", "pass123")
```

---

## 🆕 **Nuevas Funcionalidades (v1.0.0)**

### 📊 **Dashboard Completo**
- **Vista General**: Estadísticas en tiempo real de ventas, compras, inventario
- **Stock Bajo**: Alertas automáticas con niveles de urgencia
- **Gráficos**: Datos para visualizaciones de ventas y tendencias
- **Top Productos**: Productos más vendidos por cantidad y revenue
- **Rendimiento Proveedores**: Análisis de actividad de proveedores

**Endpoints:**
```bash
GET /api/dashboard/overview/              # Estadísticas generales
GET /api/dashboard/low_stock/             # Alertas stock bajo
GET /api/dashboard/sales_chart/?days=30   # Gráfico de ventas
GET /api/dashboard/top_products/          # Top productos
```

### 📤 **Exportación Avanzada**
- **Múltiples formatos**: CSV y Excel
- **Filtros personalizados**: Por fechas, estado, proveedor
- **Reportes completos**: Ventas, compras, inventario, proveedores

**Endpoints:**
```bash
GET /api/export/sales/?format=excel&start_date=2024-01-01
GET /api/export/inventory/?format=csv&include_zero=false
GET /api/export/suppliers_report/?days=90
```

### ⚡ **Operaciones Batch (Masivas)**
- **Actualización de precios**: Múltiples productos simultáneamente
- **Gestión de stock**: Actualizar stock mínimo masivamente
- **Creación masiva**: Productos con variantas en batch
- **Compras masivas**: Múltiples proveedores y productos

**Endpoints:**
```bash
POST /api/batch/update_prices/           # Actualizar precios
POST /api/batch/create_products_batch/   # Crear productos
POST /api/batch/bulk_purchase/           # Compras masivas
```

### 🔔 **Sistema de Notificaciones Inteligente**
- **Alertas de stock**: Críticas, advertencias, informativas
- **Resumen diario**: Actividades del día y comparativas
- **Recomendaciones**: Sugerencias de proveedores basadas en stock
- **Detección de anomalías**: Movimientos inusuales o patrones extraños
- **Métricas de rendimiento**: KPIs de inventario

**Endpoints:**
```bash
GET /api/notifications/low_stock_alerts/     # Alertas stock
GET /api/notifications/daily_summary/        # Resumen diario
GET /api/notifications/movement_anomalies/  # Anomalías
```

### 🔍 **Búsqueda y Filtros Avanzados**
- **Búsqueda full-text**: En productos, ventas, proveedores
- **Paginación global**: 20 elementos por página
- **Filtros exactos**: Por campos específicos
- **Ordenamiento personalizado**: Múltiples criterios

**Ejemplos:**
```bash
GET /api/products/?search=camisa&brand=Nike&active=true
GET /api/sales/?status=completed&ordering=-created_at
GET /api/purchases/?supplier=1&start_date=2024-01-01
```

---

## 📚 **Documentación Completa Actualizada**

### 📖 **API Reference Completa**
- **[Documentación Detallada](docs/API.md)** - Guía completa de todos los endpoints
- **[Swagger UI](http://localhost:8000/api/docs/)** - Documentación interactiva
- **[ReDoc](http://localhost:8000/api/redoc/)** - Documentación alternativa

### 🏗️ **Arquitectura Mejorada**
```
config/inventory/
├── dashboard/           # 📊 Estadísticas y reportes
├── export/             # 📤 Exportación CSV/Excel
├── batch/              # ⚡ Operaciones masivas
├── notifications/      # 🔔 Sistema de alertas
├── purchase/           # 🛒 Gestión de compras
├── sales/              # 🛍️ Ventas y devoluciones
├── suppliers/          # 👥 Proveedores
├── products/           # 📦 Catálogo de productos
└── core/               # 🔧 Servicios centralizados
```

---

## API Endpoints Principales

### 🔐 **Autenticación:**
- `POST /api/token/` - Obtener token JWT
- `POST /api/token/refresh/` - Refrescar token

### 👥 **Gestión de Usuarios:**
- `GET/POST /api/users/` - Listar/Crear usuarios (Managers)
- `GET/POST /api/groups/` - Listar/Crear grupos (Managers)

### 📦 **Productos y Catálogo:**
- `GET/POST /api/products/` - Listar/Crear productos (con búsqueda y filtros)
- `GET/POST /api/product-variants/` - Variantas (con búsqueda avanzada)
- `GET/POST /api/product-images/` - Imágenes de productos

### 🛍️ **Ventas y Devoluciones:**
- `GET/POST /api/sales/` - Listar/Crear ventas (con búsqueda y filtros)
- `POST /api/sales/{id}/confirm/` - Confirmar ventas
- `GET/POST /api/sale-details/` - Detalles de venta
- `GET/POST /api/sale-returns/` - Devoluciones de clientes

### 🛒 **Compras y Proveedores:**
- `GET/POST /api/purchases/` - Listar/Crear compras (con filtros)
- `POST /api/purchases/bulk_purchase/` - Compras masivas
- `GET/POST /api/suppliers/` - Proveedores
- `GET/POST /api/supplier-returns/` - Devoluciones a proveedores

### 📊 **Dashboard y Estadísticas:**
- `GET /api/dashboard/overview/` - Vista general con KPIs
- `GET /api/dashboard/low_stock/` - Alertas de stock bajo
- `GET /api/dashboard/sales_chart/` - Gráficos de ventas
- `GET /api/dashboard/top_products/` - Productos más vendidos
- `GET /api/dashboard/recent_movements/` - Movimientos recientes
- `GET /api/dashboard/supplier_performance/` - Rendimiento proveedores

### 📤 **Exportación de Datos:**
- `GET /api/export/sales/` - Exportar ventas (CSV/Excel)
- `GET /api/export/purchases/` - Exportar compras
- `GET /api/export/inventory/` - Exportar inventario actual
- `GET /api/export/movements/` - Exportar movimientos
- `GET /api/export/suppliers_report/` - Reporte de proveedores

### ⚡ **Operaciones Batch (Masivas):**
- `POST /api/batch/update_prices/` - Actualizar precios masivamente
- `POST /api/batch/update_stock_minimum/` - Actualizar stock mínimo
- `POST /api/batch/create_products_batch/` - Crear productos masivamente
- `POST /api/batch/bulk_purchase/` - Compras masivas
- `POST /api/batch/bulk_adjustments/` - Ajustes masivos
- `POST /api/batch/toggle_products_status/` - Activar/desactivar productos

### 🔔 **Notificaciones y Alertas:**
- `GET /api/notifications/low_stock_alerts/` - Alertas de stock bajo
- `GET /api/notifications/daily_summary/` - Resumen diario
- `GET /api/notifications/supplier_recommendations/` - Recomendaciones
- `GET /api/notifications/movement_anomalies/` - Detección de anomalías
- `GET /api/notifications/performance_metrics/` - Métricas de rendimiento

### 📋 **Inventario y Movimientos:**
- `GET/POST /api/movement-inventory/` - Movimientos de stock
- `GET /api/inventory-history/` - Historial completo
- `GET/POST /api/inventory-adjustments/` - Ajustes de inventario
- `GET /api/inventory-report-daily/` - Reportes diarios
- `GET /api/inventory-snapshots/` - Snapshots de inventario

---

## Casos de Uso

### Tienda Online:
```python
# Cliente crea pedido automáticamente
order = ECommerceCustomer.create_order("cliente123", [
    {'variant_id': 1, 'quantity': 2, 'price': 10.50}
])
```

### Gestión Multi-rol:
```python
# Usuario en Sales + Inventory
assign_user_to_groups("supervisor", ["Sales", "Inventory"])
```

### Reportes y Auditoría:
```python
# Historial completo de movimientos
GET /api/inventory-history/?product=3
```

---

## Desarrollo

### Estructura Modular:
- Cada módulo es independiente
- Permisos granulares por funcionalidad
- Scripts reutilizables para configuración

### Testing:
```bash
python manage.py test
python manage.py test inventory.tests
```

### API Documentation:
```bash
# Generar documentación
python manage.py spectacular --file schema.yml
```

---

## 📞 **Soporte y Contribuciones**

### **🐛 Issues y Bugs:**
- Reportar en GitHub Issues
- Incluir logs y pasos para reproducir

### **🤝 Contribuciones:**
- Fork del repositorio
- Branch `feature/nueva-funcionalidad`
- Pull Request con tests

---

## 📄 **Licencia**

MIT License - Ver archivo LICENSE para detalles

---

## 🔗 **Enlaces Útiles**

- **📖 Documentación técnica**: `config/inventory/README.md`
- **📋 Arquitectura**: `config/inventory/docs/ARCHITECTURE.md`
- **🛠️ Scripts**: `config/inventory/scripts/README.md`
- **🚀 Guía de producción**: `README_PRODUCTION.md`

---

*Para más detalles técnicos, consulta la documentación en `config/inventory/`* 📚
