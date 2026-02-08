"""
Serializers principal - Importaciones desde módulos organizados
"""
from .users.serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserManagementSerializer,
    GroupSerializer,
)
from .sales.serializers import (
    SaleCreateSerializer,
    SaleReadSerializer,
    SaleDetailCreateSerializer,
    SaleDetailReadSerializer,
    EmptySerializer,
)
from .products.serializers import (
    ProductSerializer,
    ProductReadSerializer,
    ProductVariantSerializer,
    ProductImageSerializer,
)
from .inventory_management.serializers import (
    MovementInventorySerializer,
    InventoryHistorySerializer,
    InventorySnapshotSerializer,
    DailyInventorySummarySerializer,
)

# Exportar todos los serializers para que estén disponibles
__all__ = [
    # Users
    'UserSerializer',
    'UserCreateSerializer',
    'UserManagementSerializer',
    'GroupSerializer',
    
    # Sales
    'SaleCreateSerializer',
    'SaleReadSerializer',
    'SaleDetailCreateSerializer',
    'SaleDetailReadSerializer',
    'EmptySerializer',
    
    # Products
    'ProductSerializer',
    'ProductReadSerializer',
    'ProductVariantSerializer',
    'ProductImageSerializer',
    
    # Inventory Management
    'MovementInventorySerializer',
    'InventoryHistorySerializer',
    'DailyInventorySummarySerializer',
    'InventorySnapshotSerializer',


]
