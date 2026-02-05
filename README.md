# Golos Inventory

**Sistema de gestión de inventario para productos y ventas**

Desarrollado por David Chimbaco

## 🚀 Características

- Gestión completa de inventario
- Control de productos y ventas
- API REST con Django REST Framework
- Autenticación JWT
- Documentación automática con DRF Spectacular
- Interfaz administrativa de Django

## 📋 Requisitos

- Python 3.8+
- pip

## 🛠️ Instalación Local

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd golos-inventory
```

### 2. Crear entorno virtual
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
cd config
pip install -r ../requirements.txt
```

### 4. Configurar variables de entorno
Crea el archivo `config/.env`:
```env
SECRET_KEY=django-insecure-tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

> **Importante**: Genera tu propia SECRET_KEY con:
> ```bash
> python -c "import secrets; print('django-insecure-' + secrets.token_urlsafe(50))"
> ```

### 5. Migrar la base de datos
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Crear superusuario (opcional)
```bash
python manage.py createsuperuser
```

### 7. Iniciar el servidor
```bash
python manage.py runserver
```

La aplicación estará disponible en:
- **API**: http://localhost:8000/api/
- **Admin**: http://localhost:8000/admin/
- **Documentación**: http://localhost:8000/api/docs/

## 📚 Uso de la API

### Autenticación
La API usa JWT tokens. Para obtener un token:
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "tu_usuario", "password": "tu_password"}'
```

### Endpoints principales
- `/api/` - Root API
- `/api/products/` - Gestión de productos
- `/api/sales/` - Gestión de ventas
- `/api/docs/` - Documentación interactiva

## 🔧 Desarrollo

### Estructura del proyecto
```
golos-inventory/
├── config/
│   ├── manage.py
│   ├── config/
│   │   ├── settings.py
│   │   └── urls.py
│   └── inventory/
│       ├── models.py
│       ├── views.py
│       └── serializers.py
├── .venv/
├── requirements.txt
└── README.md
```

### Comandos útiles
```bash
# Crear nuevas migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Ejecutar tests
python manage.py test

# Recolectar archivos estáticos
python manage.py collectstatic

# Servidor de desarrollo
python manage.py runserver
```

## 🤝 Contribuir

1. Fork del proyecto
2. Crear una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de los cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Para más detalles, ver el archivo [LICENSE](LICENSE).

## 👨‍💻 Autor

**David Chimbaco**
- Desarrollador de Software
- Creador de Golos Inventory

---

*Si encuentras algún bug o tienes sugerencias, por favor abre un issue en el repositorio.*
