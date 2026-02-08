"""
Módulo de gestión de ventas
"""

from .views import SaleViewSet, SaleDetailViewSet
from .serializers import (
    SaleCreateSerializer,
    SaleReadSerializer,
    SaleDetailCreateSerializer,
    SaleDetailReadSerializer,
    EmptySerializer,
)

__all__ = [
    'SaleViewSet',
    'SaleDetailViewSet',
    'SaleCreateSerializer',
    'SaleReadSerializer',
    'SaleDetailCreateSerializer',
    'SaleDetailReadSerializer',
    'EmptySerializer',
]
