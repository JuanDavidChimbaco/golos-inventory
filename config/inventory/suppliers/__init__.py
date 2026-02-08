"""
Módulo de gestión de proveedores para Golos Inventory
"""

from inventory.models import Supplier
from .serializers import SupplierSerializer, SupplierSimpleSerializer
from .views import SupplierViewSet

__all__ = [
    "Supplier",
    "SupplierSerializer", 
    "SupplierSimpleSerializer",
    "SupplierViewSet",
]
