# Scripts de utilidad (inventory/scripts)

Scripts para setup y operacion inicial del backend.

## Archivos

- `setup_permissions.py`: crea/actualiza grupos y permisos
- `user_management.py`: helpers para asignar grupos y revisar permisos
- `ecommerce_integration.py`: ejemplos de integracion para clientes/pedidos

## Uso

Ejecutar desde `golos-inventory/config`:

```bash
python manage.py shell < inventory/scripts/setup_permissions.py
```

## Grupos creados por setup_permissions

- `Customers`
- `Sales`
- `Inventory`
- `StoreOps`
- `Managers`

## Cuando ejecutarlo

- primer setup de un ambiente nuevo
- despliegue inicial en staging/produccion
- cuando cambie la matriz de permisos

## Verificacion rapida

Despues de ejecutar script:

1. validar grupos en Django Admin
2. asignar usuario operativo a `StoreOps`
3. validar acceso a `GET /api/store/ops/summary/`

## Nota

Si agregas nuevos permisos o grupos, actualiza:

- `setup_permissions.py`
- este README
