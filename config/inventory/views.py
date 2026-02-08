"""
Views principal - Importaciones desde módulos organizados
"""

from .users.views import UserViewSet, GroupViewSet
from .sales.views import SaleViewSet, SaleDetailViewSet, SaleReturnViewSet
from .suppliers.views import SupplierViewSet, SupplierReturnViewSet
from .products.views import ProductViewSet, ProductVariantViewSet, ProductImageViewSet
from .inventory_management.views import (
    MovementInventoryViewSet,
    InventoryHistoryViewSet,
    InventoryReportDailyViewSet,
    InventorySnapshotViewSet,
    InventoryCloseMonthView,
    AdjustmentViewSet,
)
from .purchase.views import PurchaseViewSet
from .dashboard.views import DashboardViewSet
from .export.views import ExportViewSet
from .batch.views import BatchOperationsViewSet
from .notifications.views import NotificationViewSet

# Exportar todos los ViewSets para que estén disponibles
__all__ = [
    # Users
    "UserViewSet",
    "GroupViewSet",
    # Sales
    "SaleViewSet",
    "SaleDetailViewSet",
    "SaleReturnViewSet",
    # Suppliers
    "SupplierViewSet",
    "SupplierReturnViewSet",
    # Products
    "ProductViewSet",
    "ProductVariantViewSet",
    "ProductImageViewSet",
    # Inventory Management
    "MovementInventoryViewSet",
    "InventoryHistoryViewSet",
    "InventoryReportDailyViewSet",
    "InventorySnapshotViewSet",
    "InventoryCloseMonthView",
    "AdjustmentViewSet",
    # Purchase
    "PurchaseViewSet",
    # Dashboard
    "DashboardViewSet",
    # Export
    "ExportViewSet",
    # Batch
    "BatchOperationsViewSet",
    # Notifications
    "NotificationViewSet",
]
