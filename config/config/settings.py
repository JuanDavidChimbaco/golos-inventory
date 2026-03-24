"""
settings.py — Configuración BASE de Golos Inventory
────────────────────────────────────────────────────
No usar directamente. Heredar desde:
  - settings_dev.py       → desarrollo local
  - settings_production.py → servidor / Docker
"""

from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

# ─── Rutas ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Carga el .env que esté junto a manage.py (config/.env)
load_dotenv(BASE_DIR / '.env')

# ─── Seguridad ───────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-solo-para-dev-cambia-esto')

DEBUG = False  # cada entorno lo sobreescribe

ALLOWED_HOSTS = []  # cada entorno lo sobreescribe

# ─── Aplicaciones ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terceros
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    'rest_framework_simplejwt',
    'django_filters',
    'storages',
    # Propias
    'inventory.apps.InventoryConfig',
]

# ─── Middleware ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ─── Channels (WebSockets) ───────────────────────────────────────────────────
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.getenv('REDIS_HOST', '127.0.0.1'), int(os.getenv('REDIS_PORT', 6379)))],
        },
    },
}
# Fallback to InMemoryChannelLayer in local dev if Redis is explicitly disabled
if os.getenv('USE_IN_MEMORY_CHANNEL_LAYER', 'False').lower() == 'true':
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# ─── Contraseñas ─────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internacionalización ────────────────────────────────────────────────────
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ─── Archivos estáticos ──────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Auto field ──────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Django REST Framework ───────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# ─── JWT ─────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME', '60'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME', '10080'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'PREPROCESSING_HOOKS': [],
    'POSTPROCESSING_HOOKS': ['config.urls.postprocess_jwt_tags'],
}

# ─── drf-spectacular (Swagger) ───────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'Golos Inventory API',
    'DESCRIPTION': 'Sistema de gestión de inventario para productos y ventas',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'docExpansion': 'none',
    },
    'TAGS': [
        {'name': 'Authentication',       'description': 'Autenticación JWT'},
        {'name': 'Users',                'description': 'Gestión de usuarios'},
        {'name': 'Groups',               'description': 'Gestión de grupos'},
        {'name': 'Permissions',          'description': 'Permisos por grupo'},
        {'name': 'Sales',                'description': 'Ventas'},
        {'name': 'SalesReturns',         'description': 'Devoluciones'},
        {'name': 'SalesDetails',         'description': 'Detalles de venta'},
        {'name': 'Products',             'description': 'Catálogo de productos'},
        {'name': 'ProductsVariants',     'description': 'Variantes'},
        {'name': 'ProductsImages',       'description': 'Imágenes de productos'},
        {'name': 'Inventory',            'description': 'Movimientos de inventario'},
        {'name': 'InventoryHistory',     'description': 'Historial'},
        {'name': 'InventoryReportDaily', 'description': 'Reporte diario'},
        {'name': 'InventorySnapshots',   'description': 'Snapshots mensuales'},
        {'name': 'InventoryCloseMonth',  'description': 'Cierre mensual'},
        {'name': 'InventoryAdjustments', 'description': 'Ajustes manuales'},
        {'name': 'Batch',                'description': 'Operaciones masivas'},
        {'name': 'Suppliers',            'description': 'Proveedores'},
        {'name': 'SuppliersReturns',     'description': 'Devoluciones a proveedores'},
        {'name': 'Dashboard',            'description': 'Estadísticas'},
        {'name': 'Export',               'description': 'Exportaciones'},
        {'name': 'Notifications',        'description': 'Notificaciones'},
        {'name': 'Purchase',             'description': 'Compras'},
        {'name': 'Store',                'description': 'Tienda en línea'},
    ],
}

# ─── Backblaze B2 ────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID = os.getenv('BACKBLAZE_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('BACKBLAZE_APPLICATION_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('BACKBLAZE_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = os.getenv('BACKBLAZE_ENDPOINT')
AWS_S3_REGION_NAME = os.getenv('BACKBLAZE_REGION')
AWS_S3_KEY_NAME = os.getenv('BACKBLAZE_KEY_NAME')
AWS_DEFAULT_ACL = 'private'
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# ─── Wompi ───────────────────────────────────────────────────────────────────
WOMPI_API_BASE_URL = os.getenv('WOMPI_API_BASE_URL', 'https://production.wompi.co/v1')
WOMPI_CHECKOUT_BASE_URL = os.getenv('WOMPI_CHECKOUT_BASE_URL', 'https://checkout.wompi.co/p/')
WOMPI_PUBLIC_KEY = os.getenv('WOMPI_PUBLIC_KEY', '')
WOMPI_PRIVATE_KEY = os.getenv('WOMPI_PRIVATE_KEY', '')
WOMPI_INTEGRITY_SECRET = os.getenv('WOMPI_INTEGRITY_SECRET', '')
WOMPI_EVENTS_SECRET = os.getenv('WOMPI_EVENTS_SECRET', '')
WOMPI_REDIRECT_URL = os.getenv('WOMPI_REDIRECT_URL', 'http://localhost:8080/store/order-status')

# ─── Store automation ────────────────────────────────────────────────────────
STORE_AUTO_ADVANCE_ENABLED = os.getenv('STORE_AUTO_ADVANCE_ENABLED', 'True').lower() == 'true'
STORE_AUTO_TO_PROCESSING_MINUTES = int(os.getenv('STORE_AUTO_TO_PROCESSING_MINUTES', '5'))
STORE_AUTO_TO_SHIPPED_MINUTES = int(os.getenv('STORE_AUTO_TO_SHIPPED_MINUTES', '120'))
STORE_AUTO_TO_DELIVERED_MINUTES = int(os.getenv('STORE_AUTO_TO_DELIVERED_MINUTES', '1440'))
STORE_AUTO_TO_COMPLETED_MINUTES = int(os.getenv('STORE_AUTO_TO_COMPLETED_MINUTES', '2880'))

# ─── Shipping ────────────────────────────────────────────────────────────────
STORE_SHIPPING_ENABLED = os.getenv('STORE_SHIPPING_ENABLED', 'True').lower() == 'true'
STORE_SHIPPING_AUTO_CREATE = os.getenv('STORE_SHIPPING_AUTO_CREATE', 'True').lower() == 'true'
STORE_SHIPPING_PROVIDER = os.getenv('STORE_SHIPPING_PROVIDER', 'mock')
STORE_SHIPPING_CARRIER_NAME = os.getenv('STORE_SHIPPING_CARRIER_NAME', 'LocalCarrier')
STORE_SHIPPING_MAX_DELIVERY_HOURS = int(os.getenv('STORE_SHIPPING_MAX_DELIVERY_HOURS', '72'))
STORE_SHIPPING_SERVICES = os.getenv('STORE_SHIPPING_SERVICES', 'eco:12000:72,standard:18000:48,express:25000:24')
STORE_SHIPPING_WEBHOOK_SECRET = os.getenv('STORE_SHIPPING_WEBHOOK_SECRET', '')
STORE_SHIPPING_API_BASE_URL = os.getenv('STORE_SHIPPING_API_BASE_URL', '')
STORE_SHIPPING_CREATE_PATH = os.getenv('STORE_SHIPPING_CREATE_PATH', '/shipments')
STORE_SHIPPING_API_KEY = os.getenv('STORE_SHIPPING_API_KEY', '')
STORE_SHIPPING_AUTH_HEADER = os.getenv('STORE_SHIPPING_AUTH_HEADER', 'Authorization')
STORE_SHIPPING_AUTH_PREFIX = os.getenv('STORE_SHIPPING_AUTH_PREFIX', 'Bearer ')
STORE_SHIPPING_API_TIMEOUT_SECONDS = int(os.getenv('STORE_SHIPPING_API_TIMEOUT_SECONDS', '15'))

# ─── Margen de rentabilidad ──────────────────────────────────────────────────
STORE_MARGIN_GUARD_ENABLED = os.getenv('STORE_MARGIN_GUARD_ENABLED', 'False').lower() == 'true'
STORE_MARGIN_MIN_PERCENT = os.getenv('STORE_MARGIN_MIN_PERCENT', '0')
STORE_MARGIN_WOMPI_PERCENT = os.getenv('STORE_MARGIN_WOMPI_PERCENT', '2.65')
STORE_MARGIN_WOMPI_FIXED_FEE = os.getenv('STORE_MARGIN_WOMPI_FIXED_FEE', '0')
STORE_MARGIN_WOMPI_VAT_PERCENT = os.getenv('STORE_MARGIN_WOMPI_VAT_PERCENT', '19')
STORE_MARGIN_PACKAGING_COST = os.getenv('STORE_MARGIN_PACKAGING_COST', '0')
STORE_MARGIN_RISK_PERCENT = os.getenv('STORE_MARGIN_RISK_PERCENT', '0')
STORE_MARGIN_DEFAULT_WEIGHT_PER_ITEM_GRAMS = int(os.getenv('STORE_MARGIN_DEFAULT_WEIGHT_PER_ITEM_GRAMS', '900'))
STORE_MARGIN_DEFAULT_SHIPPING_COST = os.getenv('STORE_MARGIN_DEFAULT_SHIPPING_COST', '0')
STORE_MARGIN_SHIPPING_COST_MATRIX = os.getenv(
    'STORE_MARGIN_SHIPPING_COST_MATRIX',
    'local:2000:0,regional:2000:0,national:2000:0',
)

# ─── Notificaciones en tiempo real ───────────────────────────────────────────
NOTIFICATIONS_ENABLED = os.getenv('NOTIFICATIONS_ENABLED', 'True').lower() == 'true'
NOTIFICATIONS_MANAGER_PHONE = os.getenv('NOTIFICATIONS_MANAGER_PHONE', '')
NOTIFICATIONS_MANAGER_EMAIL = os.getenv('NOTIFICATIONS_MANAGER_EMAIL', '')
NOTIFICATIONS_WHATSAPP_URL = os.getenv('NOTIFICATIONS_WHATSAPP_URL', '')
NOTIFICATIONS_WHATSAPP_TOKEN = os.getenv('NOTIFICATIONS_WHATSAPP_TOKEN', '')
STORE_FRONTEND_URL = os.getenv('STORE_FRONTEND_URL', 'http://localhost:3000')
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
