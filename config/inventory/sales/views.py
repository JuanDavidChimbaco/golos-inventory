"""
Views para gestión de ventas
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count
from ..models import Sale, SaleDetail, MovementInventory
from ..core.services import confirm_sale, create_sale_return
from .serializers import (
    SaleCreateSerializer,
    SaleReadSerializer,
    SaleDetailCreateSerializer,
    SaleDetailReadSerializer,
    SaleReturnCreateSerializer,
    SaleReturnSerializer,
)

@extend_schema(tags=['Sales'])
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
    filterset_fields = ['status', 'is_order']
    search_fields = ['customer']
    ordering_fields = ['created_at', 'updated_at', 'total', 'customer']
    ordering = ['-created_at']

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
            confirm_sale(sale.id, request.user)
            return Response({'message': 'Venta confirmada exitosamente'}, status=status.HTTP_200_OK)
        except ValidationError as e:
            raise DRFValidationError(str(e))


@extend_schema(tags=['SalesReturns'])
class SaleReturnViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de devoluciones de ventas
    
    - Lectura: Usuarios autenticados con permiso view_movement_inventory
    - Creación: Usuarios autenticados con permiso add_movement_inventory
    """
    queryset = MovementInventory.objects.filter(
        movement_type=MovementInventory.MovementType.SALE_RETURN
    ).select_related('variant', 'variant__product')
    serializer_class = SaleReturnSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SaleReturnCreateSerializer
        return SaleReturnSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por venta
        sale_id = self.request.query_params.get('sale')
        if sale_id:
            queryset = queryset.filter(observation__contains=f'venta #{sale_id}')
        
        # Filtrar por producto
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(variant__product_id=product_id)
        
        # Filtrar por rango de fechas
        from datetime import datetime
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=end_date)
            except ValueError:
                pass
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Crear devolución de venta usando el servicio del core"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Preparar items para el servicio
            items = []
            for item in serializer.validated_data['items']:
                items.append({
                    'sale_detail_id': item['sale_detail_id'],
                    'quantity': item['quantity']
                })
            
            # Usar el servicio del core
            movements = create_sale_return(
                sale_id=serializer.validated_data['sale_id'],
                items=items,
                reason=serializer.validated_data.get('reason', 'Devolución de cliente'),
                user=request.user
            )
            
            # Agregar razón individual a cada movimiento si se proporcionó
            for i, item in enumerate(serializer.validated_data['items']):
                if item.get('reason'):
                    movements[i].observation = f"{movements[i].observation} - {item['reason']}"
                    movements[i].save()
            
            return Response({
                'message': f'Se crearon {len(movements)} devoluciones exitosamente',
                'returns': SaleReturnSerializer(movements, many=True, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error al crear devolución: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def return_stats(self, request):
        """Obtener estadísticas de devoluciones de ventas"""
        queryset = self.get_queryset()
        
        # Estadísticas generales
        total_returns = queryset.count()
        total_quantity = queryset.aggregate(total=Sum('quantity'))['total'] or 0
        
        # Devoluciones por producto
        product_stats = queryset.values(
            'variant__product__name', 'variant__product__id'
        ).annotate(
            total_quantity=Sum('quantity'),
            return_count=Count('id')
        ).order_by('-total_quantity')
        
        return Response({
            'total_returns': total_returns,
            'total_quantity': total_quantity,
            'product_stats': list(product_stats)
        })
    
    @action(detail=False, methods=['get'])
    def sale_returns(self, request):
        """Obtener devoluciones de una venta específica"""
        sale_id = request.query_params.get('sale_id')
        
        if not sale_id:
            return Response(
                {'error': 'Se requiere sale_id'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            sale = Sale.objects.get(id=sale_id)
            returns = self.get_queryset().filter(observation__contains=f'venta #{sale_id}')
            
            return Response({
                'sale': {
                    'id': sale.id,
                    'customer': sale.customer,
                    'status': sale.status,
                    'total': sale.total
                },
                'returns': SaleReturnSerializer(returns, many=True).data,
                'summary': {
                    'total_returns': returns.count(),
                    'total_quantity': returns.aggregate(total=Sum('quantity'))['total'] or 0
                }
            })
            
        except Sale.DoesNotExist:
            return Response(
                {'error': 'Venta no encontrada'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            confirm_sale(sale_id=sale.id, user=request.user)
            return Response(
                {"status": "sale confirmed", "sale_id": sale.id},
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            raise DRFValidationError(str(e))


@extend_schema(tags=['SalesDetails'])
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
