"""
settings_dev.py — Configuración de DESARROLLO local
────────────────────────────────────────────────────
Uso: DJANGO_SETTINGS_MODULE=config.settings_dev
     python manage.py runserver
"""

from .settings import *

# ─── Modo desarrollo ─────────────────────────────────────────────────────────
DEBUG = True

ALLOWED_HOSTS = ['*']  # En dev aceptamos cualquier host

# ─── Base de datos local (SQLite, sin configurar nada) ───────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ─── CORS permisivo en dev ───────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ─── Email: muestra en consola, sin configurar SMTP ─────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ─── Sin SSL en desarrollo ───────────────────────────────────────────────────
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ─── Logging simple en consola ───────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # cambia a DEBUG para ver todas las queries SQL
            'propagate': False,
        },
    },
}

# ─── Django Debug Toolbar (opcional, instala con pip install django-debug-toolbar) ───
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# INTERNAL_IPS = ['127.0.0.1']
