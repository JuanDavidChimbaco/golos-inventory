# Golos Inventory

Sistema de inventario, ventas y tienda online (Django + DRF) con permisos por grupos y flujo de pedidos para e-commerce.

## Estado actual

- Backend modular con API REST y JWT.
- Tienda publica (`/api/store/*`) con:
  - catalogo, carrito y checkout
  - pagos Wompi (pay, verify y webhook)
  - operacion StoreOps (resumen, pedidos, cambios de estado)
  - registro de guia manual y webhook de transportadora
- Control de inventario conectado al flujo de ordenes (descuento de stock en estados de pago/proceso).

## Requisitos

- Python 3.11+
- pip
- Entorno virtual

## Inicio rapido (local)

```bash
git clone https://github.com/JuanDavidChimbaco/golos-inventory.git
cd golos-inventory
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
cd config
python manage.py migrate
python manage.py shell < inventory/scripts/setup_permissions.py
python manage.py runserver
```

## URLs utiles

- Swagger: `http://127.0.0.1:8000/api/docs/`
- ReDoc: `http://127.0.0.1:8000/api/redoc/`
- Admin: `http://127.0.0.1:8000/admin/`

## Grupos base

El script `inventory/scripts/setup_permissions.py` crea/actualiza:

- `Customers`
- `Sales`
- `Inventory`
- `StoreOps`
- `Managers`

## Variables de entorno clave

Revisa y completa:

- `config/.env.local`
- `config/.env.production`
- `config/.env.local.example`
- `config/.env.production.example`

Especialmente para produccion:

- `DEBUG=False`
- `ALLOWED_HOSTS=...`
- configuracion DB
- llaves Wompi (public/private/events/integrity segun ambiente)
- variables de shipping/store margin

## Comandos operativos recomendados

```bash
# validar proyecto
python manage.py check

# aplicar migraciones
python manage.py migrate

# tests (ejemplo)
python manage.py test inventory.tests.StorePublicApiTest
```

## Documentacion interna

- App inventory: `config/inventory/README.md`
- Scripts: `config/inventory/scripts/README.md`
- Produccion: `README_PRODUCTION.md`

## Nota importante

Cada vez que bajes cambios nuevos en servidor, ejecuta siempre:

1. `pip install -r requirements.txt` (si hubo cambios)
2. `python manage.py migrate`
3. reinicio de servicio (gunicorn/uvicorn y nginx)
