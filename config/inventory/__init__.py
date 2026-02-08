"""
Inventory App - Golos Inventory System
Gestión de inventario con optimización de imágenes y control de stock
"""

# Version de la app
__version__ = '1.0.0'

# Configuración por defecto
DEFAULT_CONFIG = {
    'MAX_IMAGE_SIZE': 2 * 1024 * 1024,  # 2MB
    'ALLOWED_IMAGE_FORMATS': ['JPEG', 'PNG', 'WEBP'],
    'MAX_IMAGE_DIMENSIONS': (1200, 1200),
    'IMAGE_QUALITY': 80,
}

# Constantes de la aplicación
APP_NAME = 'Golos Inventory'
APP_DESCRIPTION = 'Sistema de gestión de inventario para productos y ventas'

# Importaciones lazy (solo cuando se necesiten)
def get_models():
    """Importación lazy de modelos para evitar circular imports"""
    from .models import (
        Product,
        ProductVariant,
        ProductImage,
        Sale,
        SaleDetail,
        MovementInventory,
        AuditLog,
    )
    return {
        'Product': Product,
        'ProductVariant': ProductVariant,
        'ProductImage': ProductImage,
        'Sale': Sale,
        'SaleDetail': SaleDetail,
        'MovementInventory': MovementInventory,
        'AuditLog': AuditLog,
    }

def get_services():
    """Importación lazy de servicios"""
    from .services import (
        ImageService,
        confirm_sale,
    )
    return {
        'ImageService': ImageService,
        'confirm_sale': confirm_sale,
    }

def get_permissions():
    """Importación lazy de permisos"""
    from .permissions import (
        IsAdminOrReadOnly,
        IsSalesUserOrAdmin,
        IsInventoryUserOrAdmin,
        CanConfirmSales,
    )
    return {
        'IsAdminOrReadOnly': IsAdminOrReadOnly,
        'IsSalesUserOrAdmin': IsSalesUserOrAdmin,
        'IsInventoryUserOrAdmin': IsInventoryUserOrAdmin,
        'CanConfirmSales': CanConfirmSales,
    }