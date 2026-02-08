"""
Documentación y metadatos para la API de Golos Inventory
Información organizada para Swagger/ReDoc
"""

# ============================================================================
# API METADATA
# ============================================================================

API_INFO = {
    'title': 'Golos Inventory API',
    'description': (
        'Sistema de gestión de inventario para productos y ventas con '
        'optimización de imágenes y control de stock'
    ),
    'version': '1.0.0',
    'contact': {
        'name': 'Golos Inventory Team',
        'email': 'support@golos-inventory.com',
    },
    'license': {
        'name': 'MIT License',
        'url': 'https://opensource.org/licenses/MIT',
    }
}

# ============================================================================
# TAGS ORGANIZADAS
# ============================================================================

API_TAGS = [
    {
        'name': 'Authentication',
        'description': 'Autenticación JWT y gestión de tokens de acceso'
    },
    {
        'name': 'Users',
        'description': 'Gestión de usuarios y grupos del sistema'
    },
    {
        'name': 'Sales',
        'description': 'Gestión de ventas y confirmación de pedidos'
    },
    {
        'name': 'Products',
        'description': 'Catálogo de productos y variantes con control de stock'
    },
    {
        'name': 'Images',
        'description': 'Gestión de imágenes de productos con optimización automática'
    },
    {
        'name': 'Inventory',
        'description': 'Movimientos de inventario y historial completo'
    },
]

# ============================================================================
# ENDPOINTS DESCRIPTIONS
# ============================================================================

ENDPOINT_DESCRIPTIONS = {
    # Authentication
    'token_obtain_pair': 'Obtener token JWT para autenticación',
    'token_refresh': 'Refrescar token JWT expirado',
    
    # Users
    'users_list': 'Listar todos los usuarios del sistema',
    'users_create': 'Crear nuevo usuario en el sistema',
    'users_retrieve': 'Obtener detalles de un usuario específico',
    'users_update': 'Actualizar información de un usuario',
    'users_destroy': 'Eliminar un usuario del sistema',
    
    # Sales
    'sales_list': 'Listar todas las ventas',
    'sales_create': 'Crear nueva venta',
    'sales_confirm': 'Confirmar venta y procesar inventario',
    'sale_details_list': 'Listar detalles de una venta específica',
    
    # Products
    'products_list': 'Listar todos los productos',
    'products_create': 'Crear nuevo producto',
    'product_variants_list': 'Listar variantes de productos',
    'product_images_list': 'Listar imágenes de productos',
    
    # Inventory
    'movement_inventory_list': 'Listar movimientos de inventario',
    'inventory_history_list': 'Historial completo con filtros avanzados',
    'inventory_report_list': 'Reporte diario de entradas y salidas',
}

# ============================================================================
# PARAMETERS DOCUMENTATION
# ============================================================================

COMMON_PARAMETERS = {
    'pagination': {
        'page': {
            'type': 'integer',
            'description': 'Número de página para paginación',
            'example': 1,
        },
        'page_size': {
            'type': 'integer', 
            'description': 'Resultados por página (default: 20)',
            'example': 20,
        }
    },
    'inventory_filters': {
        'product': {
            'type': 'integer',
            'description': 'ID del producto para filtrar historial',
            'example': 3,
        },
        'variant': {
            'type': 'integer',
            'description': 'ID de la variante específica',
            'example': 12,
        },
        'type': {
            'type': 'string',
            'description': 'Tipo de movimiento',
            'enum': ['purchase', 'sale_out', 'sale_return', 'adjustment', 'return'],
            'example': 'purchase',
        }
    },
    'report_filters': {
        'start': {
            'type': 'date',
            'description': 'Fecha de inicio del reporte (YYYY-MM-DD)',
            'example': '2026-01-01',
        },
        'end': {
            'type': 'date',
            'description': 'Fecha de fin del reporte (YYYY-MM-DD)',
            'example': '2026-01-31',
        }
    },
    'sale_filters': {
        'sale': {
            'type': 'integer',
            'description': 'ID de la venta (obligatorio)',
            'required': True,
            'example': 5,
        },
        'variant': {
            'type': 'integer',
            'description': 'Filtrar por variante específica (opcional)',
            'example': 12,
        }
    }
}

# ============================================================================
# RESPONSE EXAMPLES
# ============================================================================

RESPONSE_EXAMPLES = {
    'auth_success': {
        'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
    },
    'sale_confirmed': {
        'status': 'sale confirmed',
        'sale_id': 123,
        'message': 'Venta procesada correctamente',
    },
    'validation_error': {
        'detail': 'La imagen es demasiado grande. Máximo permitido: 2MB',
    },
    'permission_error': {
        'detail': 'You do not have permission to perform this action.',
    }
}

# ============================================================================
# ERROR CODES
# ============================================================================

ERROR_CODES = {
    400: 'Bad Request - Datos inválidos o mal formateados',
    401: 'Unauthorized - No autenticado o token inválido',
    403: 'Forbidden - No tienes permisos para esta acción',
    404: 'Not Found - Recurso no encontrado',
    413: 'Payload Too Large - Archivo demasiado grande',
    422: 'Unprocessable Entity - Error de validación de negocio',
    500: 'Internal Server Error - Error del servidor',
}

# ============================================================================
# ENDPOINT FILTERS
# ============================================================================

ENDPOINT_FILTERS = {
    'inventory_history': {
        'description': 'Historial completo de movimientos con filtros avanzados',
        'parameters': ['product', 'variant', 'type'],
        'examples': [
            '/api/inventory-history/?product=5',
            '/api/inventory-history/?variant=12&type=purchase',
            '/api/inventory-history/?product=3&variant=12&type=sale_out',
        ]
    },
    'inventory_report': {
        'description': 'Reporte diario de entradas y salidas de inventario',
        'parameters': ['start', 'end'],
        'examples': [
            '/api/inventory-report/?start=2026-01-01',
            '/api/inventory-report/?start=2026-01-01&end=2026-01-31',
        ]
    },
    'sale_confirm': {
        'description': 'Confirmar venta pendiente y procesar inventario',
        'parameters': ['sale_id'],
        'examples': [
            'POST /api/sales/123/confirm/',
        ],
        'required_permissions': ['inventory.confirm_sale'],
    },
}

# ============================================================================
# HELPERS
# ============================================================================

def get_endpoint_description(endpoint_name):
    """Obtener descripción de un endpoint"""
    return ENDPOINT_DESCRIPTIONS.get(endpoint_name, '')

def get_error_description(error_code):
    """Obtener descripción de un código de error"""
    return ERROR_CODES.get(error_code, 'Error desconocido')

def get_endpoint_filters(endpoint_name):
    """Obtener filtros de un endpoint"""
    return ENDPOINT_FILTERS.get(endpoint_name, {})

def format_api_docs():
    """Formatear documentación para Swagger/ReDoc"""
    return {
        'info': API_INFO,
        'tags': API_TAGS,
        'servers': [
            {
                'url': 'http://127.0.0.1:8000',
                'description': 'Servidor de desarrollo'
            },
            {
                'url': 'https://api.golos-inventory.com',
                'description': 'Servidor de producción'
            }
        ]
    }
