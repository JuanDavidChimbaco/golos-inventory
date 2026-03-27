# Golos Inventory

Sistema de inventario, ventas y tienda online (Django + DRF) con permisos por grupos y flujo de pedidos e-commerce.

## Estado Actual
- **Backend**: API REST con JWT y arquitectura modular
- **Tienda Pública** (`/api/store/*`): catálogo, carrito, checkout, recuperación de contraseña y pagos Wompi
- **Operaciones StoreOps**: gestión de pedidos, estados y guías
- **Inventario**: control automático de stock conectado al flujo de ventas
- **Notificaciones en Tiempo Real**: Eventos en vivo hacia el dashboard vía WebSockets (Daphne/Redis)
- **Alertas Bot**: Integración con Telegram Bot para notificaciones instantáneas de nuevas ventas
- **Reportes**: Generación y consulta de reportes financieros del negocio

## Requisitos
- Python 3.11+
- pip y entorno virtual

## Inicio Rápido (Local)

```bash
git clone https://github.com/JuanDavidChimbaco/golos-inventory.git
cd golos-inventory
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
cd config
python manage.py migrate --settings=config.settings_dev
python manage.py setup_permissions --settings=config.settings_dev
python manage.py createsuperuser --settings=config.settings_dev
python manage.py runserver --settings=config.settings_dev
```

**Nota**: Usa `--settings=config.settings_dev` en todos los comandos. Para producción, consulta `README_PRODUCTION.md`.

## URLs Útiles
- **API Docs**: `http://127.0.0.1:8000/api/docs/`
- **Admin**: `http://127.0.0.1:8000/admin/`

## Grupos de Permisos
`setup_permissions` crea: `Customers`, `Sales`, `Inventory`, `StoreOps`, `Managers`

## Configuración de Entorno
**Archivo base**: `config/.env.example` (copia como `.env` y ajusta según ambiente)

**Variables esenciales**:
- `DEBUG=False` (producción) / `DEBUG=True` (desarrollo)
- `ALLOWED_HOSTS=...` (dominios en producción)
- Configuración DB y llaves Wompi
- Variables de shipping/store margin

## Comandos Operativos
```bash
python manage.py check          # Validar proyecto
python manage.py migrate       # Aplicar migraciones
python manage.py test          # Ejecutar tests
```

## Documentación
- **App inventory**: `config/inventory/README.md`
- **Producción**: `README_PRODUCTION.md`

