# 🛠️ Scripts de Utilidad - Golos Inventory

Esta carpeta contiene scripts para facilitar la configuración y gestión del sistema.

## 📁 **Estructura de Scripts**

```
scripts/ 📁
├── 📄 README.md                # Esta guía
├── 🔧 setup_permissions.py     # Configuración inicial de permisos
├── 👥 user_management.py       # Gestión de usuarios y grupos
└── 🛒 ecommerce_integration.py  # Integración con tiendas online
```

---

## 🔧 **setup_permissions.py**

### **Propósito:**
Configurar automáticamente los grupos de usuarios y permisos del sistema.

### **¿Cuándo usarlo?**
- **Setup inicial** de nuevos entornos (dev, staging, prod)
- **Reconfiguración** después de cambios en permisos
- **Documentación** de qué permisos tiene cada grupo

### **Uso:**
```bash
# Ejecutar configuración inicial
python manage.py shell < scripts/setup_permissions.py
```

### **Grupos Configurados:**
- **Customers** (3 permisos) - Clientes e-commerce
- **Sales** (5 permisos) - Equipo de ventas  
- **Inventory** (7 permisos) - Bodegueros
- **Managers** (20 permisos) - Administradores

---

## 👥 **user_management.py**

### **Propósito:**
Ejemplos y utilidades para gestión de usuarios y grupos.

### **¿Cuándo usarlo?**
- **Asignar usuarios** a múltiples grupos
- **Verificar permisos** de usuarios específicos
- **Crear usuarios** con roles predefinidos
- **Auditoría** de permisos y grupos

### **Uso:**
```python
# Importar funciones
from inventory.scripts.user_management import (
    create_multi_role_user,
    assign_user_to_groups, 
    check_user_permissions
)

# Ejemplos
assign_user_to_groups("juan", ["Sales", "Inventory"])
check_user_permissions("juan")
```

### **Funciones Principales:**
- `create_multi_role_user()` - Crear usuario con múltiples roles
- `assign_user_to_groups()` - Asignar usuario a grupos existentes
- `check_user_permissions()` - Verificar permisos de usuario

---

## 🛒 **ecommerce_integration.py**

### **Propósito:**
Facilitar la integración con plataformas e-commerce.

### **¿Cuándo usarlo?**
- **Integración** con tiendas online
- **Creación de clientes** desde frontend
- **Procesamiento de pedidos** con validaciones
- **Verificación de stock** en tiempo real

### **Uso:**
```python
# Importar clases
from inventory.scripts.ecommerce_integration import ECommerceCustomer

# Crear cliente
customer = ECommerceCustomer.create_customer(
    username="cliente123",
    email="cliente@tienda.com",
    password="segura123"
)

# Crear pedido
order = ECommerceCustomer.create_order(
    customer_username="cliente123",
    items_data=[
        {'variant_id': 1, 'quantity': 2, 'price': 10.50}
    ]
)
```

### **Clases Principales:**
- `ECommerceCustomer` - Gestión completa de clientes
- Validación automática de stock
- Cálculo de totales
- Aislamiento de datos por cliente

---

## 🚀 **Flujo de Trabajo Recomendado**

### **🔧 Setup Inicial:**
1. **Ejecutar**: `python manage.py shell < scripts/setup_permissions.py`
2. **Verificar**: Grupos creados en Django Admin
3. **Crear usuarios base**: Admin, Managers
4. **Testear**: Permisos con `scripts/user_management.py`

### **📈 Operación Diaria:**
1. **Clientes**: Usar `ecommerce_integration.py` para registro
2. **Usuarios**: Usar `user_management.py` para gestión
3. **Permisos**: Verificar con `check_user_permissions()`
4. **Auditoría**: Revisar asignaciones de grupos

### **🔄 Mantenimiento:**
1. **Actualizar scripts** si cambian permisos
2. **Documentar cambios** en este README
3. **Testear funciones** después de actualizaciones
4. **Versionar scripts** para diferentes entornos

---

## 🎯 **Buenas Prácticas**

### **✅ Seguridad:**
- **No incluir** credenciales en los scripts
- **Validar permisos** antes de ejecutar acciones
- **Usar variables de entorno** para datos sensibles

### **✅ Mantenimiento:**
- **Documentar cambios** en este README
- **Versionar scripts** para diferentes entornos
- **Testear funciones** regularmente

### **✅ Uso:**
- **Leer la documentación** antes de usar
- **Hacer backup** antes de cambios masivos
- **Usar entornos de prueba** para testing

---

## 🛠️ **Ejecución Remota**

### **Para ejecutar scripts desde cualquier lugar:**
```python
# Desde cualquier parte del proyecto
from inventory.scripts.setup_permissions import setup_groups_and_permissions
from inventory.scripts.user_management import assign_user_to_groups
from inventory.scripts.ecommerce_integration import ECommerceCustomer

# Usar las funciones directamente
setup_groups_and_permissions()
```

---

## 📚 **Referencia Rápida**

| Script | Función Principal | Permisos Requeridos |
|--------|------------------|---------------------|
| `setup_permissions.py` | Configurar grupos y permisos | Superuser |
| `user_management.py` | Gestión de usuarios | Managers |
| `ecommerce_integration.py` | Integración e-commerce | Customers + API |

---

## 🆘 **Ayuda y Soporte**

### **Para obtener ayuda sobre funciones específicas:**
```python
# Ver ayuda de una función
help(assign_user_to_groups)

# Ver documentación de una clase
help(ECommerceCustomer)
```

### **Para reportar problemas:**
1. **Verificar** que estás usando la versión correcta del script
2. **Revisar** los permisos del usuario que ejecuta
3. **Consultar** los logs de Django para errores
4. **Documentar** el problema para futuras referencias

---

*Esta carpeta centraliza todas las utilidades del sistema para facilitar el mantenimiento y uso* 🛠️
