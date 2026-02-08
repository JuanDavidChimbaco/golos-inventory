"""
Views para gestión de ventas
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError
from ..models import Sale, SaleDetail
from ..core.services import confirm_sale
from .serializers import (
    SaleCreateSerializer,
    SaleReadSerializer,
    SaleDetailCreateSerializer,
    SaleDetailReadSerializer,
)


class SaleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de ventas
    
    - Lectura: Usuarios autenticados con permiso view_sale
    - Creación: Usuarios autenticados con permiso add_sale
    - Actualización: Usuarios autenticados con permiso change_sale
    - Confirmación: Usuarios autenticados con permiso confirm_sale
    """
    queryset = Sale.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return SaleReadSerializer
        return SaleCreateSerializer

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirma una venta pendiente:
        1. Valida stock disponible
        2. Crea movimientos de inventario
        3. Actualiza estado a 'completed'
        4. Registra en auditoría
        """
        sale = self.get_object()
        
        # Verificar permiso específico para confirmar ventas
        if not request.user.has_perm('inventory.confirm_sale'):
            raise DRFValidationError("No tienes permiso para confirmar ventas")
        
        try:
            confirm_sale(sale_id=sale.id, user=request.user)
            return Response(
                {"status": "sale confirmed", "sale_id": sale.id},
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            raise DRFValidationError(str(e))


class SaleDetailViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de detalles de ventas
    
    - Solo muestra detalles de ventas pendientes
    """
    serializer_class = SaleDetailCreateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def get_queryset(self):
        """Filtra por venta pendiente específica"""
        sale_id = self.kwargs.get('sale_pk')
        if sale_id:
            return SaleDetail.objects.filter(
                sale_id=sale_id, 
                sale__status="pending", 
                quantity__gt=0
            ).select_related('sale', 'variant', 'variant__product')
        return SaleDetail.objects.filter(
            sale__status="pending", 
            quantity__gt=0
        ).select_related('sale', 'variant', 'variant__product')

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return SaleDetailReadSerializer
        return SaleDetailCreateSerializer
