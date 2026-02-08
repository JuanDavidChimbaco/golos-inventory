"""
Views principal - Importaciones desde módulos organizados
"""

from .users.views import UserViewSet, GroupViewSet
from .sales.views import SaleViewSet, SaleDetailViewSet
from .products.views import ProductViewSet, ProductVariantViewSet, ProductImageViewSet
from .inventory_management.views import (
    MovementInventoryViewSet,
    InventoryHistoryViewSet,
    InventoryReportViewSet,
    InventorySnapshotViewSet,
    InventoryCloseMonthView,
)

# Exportar todos los ViewSets para que estén disponibles
__all__ = [
    # Users
    "UserViewSet",
    "GroupViewSet",
    # Sales
    "SaleViewSet",
    "SaleDetailViewSet",
    # Products
    "ProductViewSet",
    "ProductVariantViewSet",
    "ProductImageViewSet",
    # Inventory Management
    "MovementInventoryViewSet",
    "InventoryHistoryViewSet",
    "InventoryReportViewSet",
    "InventorySnapshotViewSet",
    "InventoryCloseMonthView",
]
