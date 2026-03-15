"""
Views principal - Importaciones desde módulos organizados
"""

from .users.views import UserViewSet, GroupViewSet, PermissionViewSet
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
from .batch.views import BatchOperationsViewSet
from .notifications.views import NotificationViewSet
from .finance.views import (
    FinancialCategoryViewSet,
    FinancialTransactionViewSet,
    CashSessionViewSet
)

# Exportar todos los ViewSets para que estén disponibles
__all__ = [
    # Users
    "UserViewSet",
    "GroupViewSet",
    "PermissionViewSet",
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
    # Batch
    "BatchOperationsViewSet",
    # Notifications
    "NotificationViewSet",
    # Finance
    "FinancialCategoryViewSet",
    "FinancialTransactionViewSet",
    "CashSessionViewSet",
]
