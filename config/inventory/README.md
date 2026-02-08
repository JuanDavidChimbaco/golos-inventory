# 📦 Golos Inventory - Sistema de Gestión con Django Permissions

## 🎯 **Arquitectura Actualizada**

```
inventory/ 📁
├── 📚 docs/                    # Documentación y metadatos API
├── 👥 users/                   # Gestión de usuarios y grupos
├── 🛍️ sales/                    # Gestión de ventas con confirmación
├── 📦 products/                # Catálogo de productos con imágenes
├── 📋 inventory_management/     # Control de stock y movimientos
├── 🔧 core/                    # Funcionalidades compartidas
│   ├── constants.py           # Constantes de grupos
│   ├── services.py            # Lógica de negocio
│   └── utils.py               # Utilidades varias
├── 🛠️ scripts/                # Scripts de configuración y ejemplos
│   ├── setup_permissions.py    # Configuración inicial de permisos
│   ├── user_management.py      # Ejemplos de gestión de usuarios
│   └── ecommerce_integration.py # Integración con tiendas online
└── 🗄️ [archivos Django]        # Configuración Django
```

## 🚀 **Inicio Rápido**

### **1. Configurar Permisos y Grupos**
```bash
# Ejecutar script de configuración
python manage.py shell < scripts/setup_permissions.py
```

### **2. Iniciar Servidor**
```bash
python manage.py runserver
```

### **3. API Documentation**
- **Swagger UI**: http://127.0.0.1:8000/api/docs/
- **ReDoc**: http://127.0.0.1:8000/api/redoc/
- **API Schema**: http://127.0.0.1:8000/api/schema/

## � **Sistema de Permisos Django**

### **Grupos de Usuarios y Permisos:**

| Grupo | Permisos Clave | Funcionalidad |
|-------|----------------|----------------|
| **Customers** | `view_product`, `add_sale`, `view_sale` | Clientes e-commerce |
| **Sales** | `view_product`, `add_sale`, `change_sale`, `confirm_sale` | Equipo de ventas |
| **Inventory** | `view_product`, `add_product`, `change_product`, `manage_inventory` | Bodegueros |
| **Managers** | **Todos los permisos** + gestión de usuarios | Administradores |

### **Permisos Personalizados:**
- `inventory.confirm_sale` - Confirmar ventas
- `inventory.manage_inventory` - Gestionar inventario

## 📁 **Estructura Modular Actualizada**

### **📚 docs/**
- `README.md` - Documentación principal
- `ARCHITECTURE.md` - Guía de arquitectura
- `docs.py` - Metadatos y tags API

### **👥 users/**
- `serializers.py` - UserSerializer, GroupSerializer
- `views.py` - UserViewSet, GroupViewSet (DjangoModelPermissions)

### **🛍️ sales/**
- `serializers.py` - SaleSerializer, SaleDetailSerializer
- `views.py` - SaleViewSet con acción `confirm()`

### **📦 products/**
- `serializers.py` - ProductSerializer, ProductImageSerializer
- `views.py` - ProductViewSet, ProductImageViewSet

### **📋 inventory_management/**
- `serializers.py` - MovementInventorySerializer
- `views.py` - MovementInventoryViewSet, InventoryHistoryViewSet

### **🔧 core/**
- `constants.py` - Solo constantes de grupos usadas
- `services.py` - confirm_sale(), ImageService
- `utils.py` - Funciones utilitarias

## 🛒 **Integración E-Commerce**

### **Flujo de Cliente:**
```python
# 1. Cliente se registra (automáticamente en grupo Customers)
customer = User.objects.create_user('cliente1', 'email@tienda.com', 'pass123')

# 2. Cliente crea pedido (API REST)
POST /api/sales/
{
    "customer": "Juan Pérez",
    "details": [
        {"variant": 1, "quantity": 2, "unit_price": 10.50}
    ]
}

# 3. Pedido queda en "pending" esperando confirmación
# 4. Equipo Sales confirma: POST /api/sales/{id}/confirm/
```

### **Scripts de Integración:**
- `scripts/ecommerce_integration.py` - Clases para integración con tiendas online
- `scripts/user_management.py` - Ejemplos de gestión de usuarios
- `scripts/setup_permissions.py` - Configuración inicial de permisos

## 🎯 **API Endpoints (40 totales)**

### **🔐 Autenticación:**
- `POST /api/token/` - Obtener token JWT
- `POST /api/token/refresh/` - Refrescar token

### **👥 Gestión de Usuarios:**
- `GET/POST /api/users/` - Listar/Crear usuarios (Managers)
- `GET/PUT/DELETE /api/users/{id}/` - Gestionar usuario (Managers)
- `GET/POST /api/groups/` - Listar/Crear grupos (Managers)

### **🛍️ Ventas:**
- `GET/POST /api/sales/` - Listar/Crear ventas
- `GET/PUT/DELETE /api/sales/{id}/` - Gestionar venta
- `POST /api/sales/{id}/confirm/` - Confirmar venta (Sales/Managers)
- `GET/POST /api/sale-details/` - Gestión de detalles

### **📦 Productos:**
- `GET/POST /api/products/` - Listar/Crear productos
- `GET/PUT/DELETE /api/products/{id}/` - Gestionar producto
- `GET/POST /api/product-variants/` - Variantas de productos
- `GET/POST /api/product-images/` - Imágenes de productos

### **� Inventario:**
- `GET/POST /api/movement-inventory/` - Movimientos de stock
- `GET/PUT/DELETE /api/movement-inventory/{id}/` - Gestionar movimiento
- `GET /api/inventory-history/` - Historial completo

## 🔧 **Configuración de Permisos**

### **Crear Usuario Multi-rol:**
```python
from inventory.scripts.user_management import assign_user_to_groups

# Usuario en Sales + Inventory
assign_user_to_groups("juan_vendedor", ["Sales", "Inventory"])
```

### **Verificar Permisos:**
```python
from inventory.scripts.user_management import check_user_permissions

check_user_permissions("juan_vendedor")
```

### **Crear Cliente E-Commerce:**
```python
from inventory.scripts.ecommerce_integration import ECommerceCustomer

customer = ECommerceCustomer.create_customer(
    username="cliente123",
    email="cliente@tienda.com", 
    password="segura123"
)
```

## 🎯 **Características Implementadas**

- ✅ **Django Permissions**: Sistema de permisos nativo y escalable
- ✅ **Modularidad**: Código organizado por funcionalidad
- ✅ **API RESTful**: 40 endpoints con Swagger/ReDoc
- ✅ **Control de Stock**: Validaciones en tiempo real
- ✅ **Gestión de Imágenes**: Optimización automática
- ✅ **Auditoría**: Registro completo de acciones
- ✅ **E-Commerce Ready**: Integración con tiendas online
- ✅ **Multi-rol**: Usuarios pueden pertenecer a múltiples grupos
- ✅ **Seguridad**: Aislamiento de datos por permisos

## 🛠️ **Scripts Útiles**

### **Configuración Inicial:**
```bash
python manage.py shell < scripts/setup_permissions.py
```

### **Gestión de Usuarios:**
```python
# Ver todos los scripts disponibles
python -c "from inventory.scripts.user_management import *; help(assign_user_to_groups)"
```

### **Integración E-Commerce:**
```python
# Ejemplos de integración
python -c "from inventory.scripts.ecommerce_integration import *; help(ECommerceCustomer)"
```

---

## 📚 **Documentación Adicional**

- `docs/ARCHITECTURE.md` - Arquitectura detallada
- `docs/docs.py` - Metadatos de la API
- `scripts/README.md` - Guía de scripts y utilidades
- `scripts/setup_permissions.py` - Configuración de permisos
- `scripts/ecommerce_integration.py` - Ejemplos de integración

*Para más detalles técnicos, consulta la documentación en `docs/`* 📚
