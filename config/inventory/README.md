# Inventory App (config/inventory)

Aplicacion principal de negocio para inventario, ventas y tienda online.

## Modulos

- `products/`: catalogo, variantes, imagenes
- `inventory_management/`: movimientos y ajustes
- `sales/`: ventas, estados, pagos y confirmacion
- `purchase/`: compras
- `suppliers/`: proveedores
- `store/`: API publica de tienda + StoreOps + Wompi + shipping
- `users/`: usuarios, grupos y permisos
- `dashboard/`, `export/`, `batch/`, `notifications/`: analitica y operacion
- `core/`: respuestas API y utilidades compartidas

## Store API (resumen)

Rutas principales en `config/config/urls.py`:

- Catalogo y branding:
  - `GET /api/store/products/`
  - `GET /api/store/products/<id>/`
  - `GET /api/store/products/featured/`
  - `GET /api/store/products/<id>/related/`
  - `GET /api/store/branding/`
- Cliente tienda:
  - `POST /api/store/auth/register/`
  - `POST /api/store/auth/login/`
  - `GET /api/store/me/orders/`
- Carrito y checkout:
  - `POST /api/store/cart/validate/`
  - `POST /api/store/checkout/`
- Estado de pedido:
  - `GET /api/store/orders/lookup/`
  - `GET /api/store/orders/<sale_id>/`
  - `POST /api/store/orders/<sale_id>/pay/`
  - `POST /api/store/orders/<sale_id>/wompi/verify/`
- Webhooks:
  - `POST /api/store/wompi/webhook/`
  - `POST /api/store/shipping/webhook/`
- Operacion tienda:
  - `GET /api/store/ops/summary/`
  - `GET /api/store/ops/orders/`
  - `PATCH /api/store/ops/orders/<sale_id>/status/`
  - `POST /api/store/ops/orders/<sale_id>/shipment/manual/`
  - `GET/PATCH /api/store/ops/branding/`

## Estados de orden

Flujo normal:

`pending -> paid -> processing -> shipped -> delivered -> completed`

Cancelacion posible segun reglas de transicion.

## Integraciones

- Wompi:
  - checkout por URL firmada
  - verificacion por redirect (verify)
  - sincronizacion por webhook
- Shipping:
  - guia manual
  - webhook de estado de transportadora

## Permisos

Grupo recomendado para operacion diaria de pedidos online:

- `StoreOps`

Grupo administrativo completo:

- `Managers`

## Scripts utiles

- `scripts/setup_permissions.py`
- `scripts/user_management.py`
- `scripts/ecommerce_integration.py`

## Mantenimiento

Despues de cambios de modelo:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py check
```
