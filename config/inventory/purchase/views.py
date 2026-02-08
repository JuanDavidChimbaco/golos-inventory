"""
    Views para la gestión de compras
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import permissions
from django.db.models import Sum, Count
from datetime import datetime

from ..models import MovementInventory, Supplier, ProductVariant
from .serializers import (
    PurchaseSerializer, 
    PurchaseCreateSerializer, 
    PurchaseDetailSerializer,
    BulkPurchaseSerializer
)
from ..core.services import (
    create_purchase, 
    create_supplier_return,
    daily_inventory_summary
)


class PurchaseViewSet(viewsets.ModelViewSet):
    """ViewSet simplificado para gestionar compras"""
    queryset = MovementInventory.objects.filter(
        movement_type=MovementInventory.MovementType.PURCHASE
    ).select_related('variant', 'variant__product', 'supplier')
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated, permissions.DjangoModelPermissions]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PurchaseCreateSerializer
        return PurchaseSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros simples
        if supplier_id := self.request.query_params.get('supplier'):
            queryset = queryset.filter(supplier_id=supplier_id)
        if product_id := self.request.query_params.get('product'):
            queryset = queryset.filter(variant__product_id=product_id)
        if start_date := self.request.query_params.get('start_date'):
            try:
                queryset = queryset.filter(created_at__date__gte=datetime.strptime(start_date, '%Y-%m-%d').date())
            except ValueError:
                pass
        if end_date := self.request.query_params.get('end_date'):
            try:
                queryset = queryset.filter(created_at__date__lte=datetime.strptime(end_date, '%Y-%m-%d').date())
            except ValueError:
                pass
        if ordering := self.request.query_params.get('ordering'):
            queryset = queryset.order_by(ordering)
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            movement = create_purchase(
                variant_id=serializer.validated_data['variant'].id,
                quantity=serializer.validated_data['quantity'],
                unit_cost=serializer.validated_data['variant'].cost,
                supplier_id=serializer.validated_data.get('supplier', {}).get('id') if serializer.validated_data.get('supplier') else None,
                user=request.user
            )
            
            if serializer.validated_data.get('observation'):
                movement.observation = serializer.validated_data['observation']
                movement.save()
            
            return Response(
                PurchaseSerializer(movement, context={'request': request}).data, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_purchase(self, request):
        serializer = BulkPurchaseSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            movements = []
            supplier = serializer.validated_data['supplier']
            observation = serializer.validated_data.get('observation', '')
            
            for item in serializer.validated_data['items']:
                movement = create_purchase(
                    variant_id=item['variant'],
                    quantity=item['quantity'],
                    unit_cost=ProductVariant.objects.get(id=item['variant']).cost,
                    supplier_id=supplier.id,
                    user=request.user
                )
                if observation:
                    movement.observation = observation
                    movement.save()
                movements.append(movement)
            
            return Response({
                'message': f'Se crearon {len(movements)} compras',
                'purchases': PurchaseDetailSerializer(movements, many=True).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def purchase_stats(self, request):
        queryset = self.get_queryset()
        
        return Response({
            'total_purchases': queryset.count(),
            'total_quantity': queryset.aggregate(total=Sum('quantity'))['total'] or 0,
            'supplier_stats': list(queryset.values('supplier__name', 'supplier__id')
                .annotate(total_quantity=Sum('quantity'), purchase_count=Count('id'))
                .order_by('-total_quantity')),
            'product_stats': list(queryset.values('variant__product__name', 'variant__product__id')
                .annotate(total_quantity=Sum('quantity'), purchase_count=Count('id'))
                .order_by('-total_quantity')),
            'daily_summary': list(daily_inventory_summary(
                request.query_params.get('start_date'),
                request.query_params.get('end_date')
            ))
        })
    
    @action(detail=False, methods=['get'])
    def supplier_purchases(self, request):
        if not (supplier_id := request.query_params.get('supplier_id')):
            return Response({'error': 'Se requiere supplier_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            purchases = self.get_queryset().filter(supplier=supplier)
            
            return Response({
                'supplier': {'id': supplier.id, 'name': supplier.name, 'nit': supplier.nit},
                'purchases': PurchaseDetailSerializer(purchases, many=True).data,
                'summary': {
                    'total_purchases': purchases.count(),
                    'total_quantity': purchases.aggregate(total=Sum('quantity'))['total'] or 0,
                    'total_amount': sum(p.quantity * p.variant.cost for p in purchases)
                }
            })
        except Supplier.DoesNotExist:
            return Response({'error': 'Proveedor no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def reverse_purchase(self, request, pk=None):
        try:
            purchase = self.get_object()
            reason = request.data.get('reason', 'Devolución de compra')
            
            return_movement = create_supplier_return(
                variant_id=purchase.variant.id,
                quantity=purchase.quantity,
                reason=f"Devolución de compra #{purchase.id}: {reason}",
                supplier_id=purchase.supplier.id if purchase.supplier else None,
                user=request.user
            )
            
            return Response({
                'message': 'Compra revertida',
                'return_movement': PurchaseDetailSerializer(return_movement).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': f'Error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)