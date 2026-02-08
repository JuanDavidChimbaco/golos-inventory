"""
Views para gestión de proveedores
"""
from rest_framework import viewsets, permissions, status
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Avg, Max, Count, Sum
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from datetime import datetime
from ..models import Supplier, MovementInventory
from ..core.services import create_purchase, create_supplier_return
from .serializers import (
    SupplierSerializer, 
    SupplierSimpleSerializer,
    SupplierReturnCreateSerializer,
    SupplierReturnSerializer,
    SupplierReturnBulkSerializer
)


@extend_schema(tags=['Suppliers'])
class SupplierViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de proveedores
    
    - Crear: Usuarios con permiso manage_suppliers
    - Actualizar: Usuarios con permiso manage_suppliers
    - Eliminar: Usuarios con permiso manage_suppliers
    - Consultar: Usuarios autenticados
    """
    queryset = Supplier.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def get_serializer_class(self):
        if self.action in ['list']:
            return SupplierSimpleSerializer
        return SupplierSerializer

    def perform_create(self, serializer):
        """Registrar usuario que crea el proveedor"""
        serializer.save(created_by=self.request.user.username)

    @action(detail=True, methods=['post'])
    def purchase(self, request, pk=None):
        """
        Crear compra a este proveedor
        
        POST /api/suppliers/{id}/purchase/
        {
            "items": [
                {"variant_id": 1, "quantity": 10, "unit_cost": 15000},
                {"variant_id": 2, "quantity": 5, "unit_cost": 12000}
            ]
        }
        """
        supplier = self.get_object()
        items = request.data.get('items', [])
        
        if not items:
            return Response(
                {'error': 'Se deben proporcionar items para la compra'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            movements = []
            for item in items:
                movement = create_purchase(
                    variant_id=item['variant_id'],
                    quantity=item['quantity'],
                    unit_cost=item['unit_cost'],
                    supplier_id=supplier.id,
                    supplier_name=supplier.name,
                    user=request.user
                )
                movements.append(movement)
            
            return Response({
                'message': f'Compra creada con {len(movements)} items',
                'movements': [{'id': m.id, 'variant': m.variant.product.name} for m in movements]
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['SuppliersReturns'])
class SupplierReturnViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de devoluciones a proveedores
    
    - Lectura: Usuarios autenticados con permiso view_movement_inventory
    - Creación: Usuarios autenticados con permiso add_movement_inventory
    """
    queryset = MovementInventory.objects.filter(
        movement_type=MovementInventory.MovementType.RETURN
    ).select_related('variant', 'variant__product', 'supplier')
    serializer_class = SupplierReturnSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SupplierReturnCreateSerializer
        return SupplierReturnSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrar por proveedor
        supplier_id = self.request.query_params.get('supplier')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Filtrar por producto
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(variant__product_id=product_id)
        
        # Filtrar por rango de fechas
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
        """Crear devolución a proveedor usando el servicio del core"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Usar el servicio del core
            movement = create_supplier_return(
                variant_id=serializer.validated_data['variant'].id,
                quantity=serializer.validated_data['quantity'],
                reason=serializer.validated_data.get('observation', 'Devolución a proveedor'),
                supplier_id=serializer.validated_data.get('supplier', {}).id if serializer.validated_data.get('supplier') else None,
                supplier_name=serializer.validated_data.get('supplier', {}).name if serializer.validated_data.get('supplier') else '',
                user=request.user
            )
            
            return Response(
                SupplierReturnSerializer(movement, context={'request': request}).data, 
                status=status.HTTP_201_CREATED
            )
            
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error al crear devolución: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_return(self, request):
        """Crear múltiples devoluciones en una sola petición"""
        serializer = SupplierReturnBulkSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            movements = []
            supplier = serializer.validated_data['supplier']
            observation = serializer.validated_data.get('observation', 'Devolución masiva a proveedor')
            
            for item in serializer.validated_data['items']:
                movement = create_supplier_return(
                    variant_id=item['variant'],
                    quantity=item['quantity'],
                    reason=observation,
                    supplier_id=supplier.id,
                    supplier_name=supplier.name,
                    user=request.user
                )
                movements.append(movement)
            
            return Response({
                'message': f'Se crearon {len(movements)} devoluciones exitosamente',
                'returns': SupplierReturnSerializer(movements, many=True, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error al crear devoluciones: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def return_stats(self, request):
        """Obtener estadísticas de devoluciones a proveedores"""
        queryset = self.get_queryset()
        
        # Estadísticas generales
        total_returns = queryset.count()
        total_quantity = queryset.aggregate(total=Sum('quantity'))['total'] or 0
        
        # Devoluciones por proveedor
        supplier_stats = queryset.values(
            'supplier__name', 'supplier__id'
        ).annotate(
            total_quantity=Sum('quantity'),
            return_count=Count('id')
        ).order_by('-total_quantity')
        
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
            'supplier_stats': list(supplier_stats),
            'product_stats': list(product_stats)
        })
    
    @action(detail=False, methods=['get'])
    def supplier_returns(self, request):
        """Obtener devoluciones de un proveedor específico"""
        supplier_id = request.query_params.get('supplier_id')
        
        if not supplier_id:
            return Response(
                {'error': 'Se requiere supplier_id'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            returns = self.get_queryset().filter(supplier=supplier)
            
            return Response({
                'supplier': {
                    'id': supplier.id,
                    'name': supplier.name,
                    'nit': supplier.nit
                },
                'returns': SupplierReturnSerializer(returns, many=True).data,
                'summary': {
                    'total_returns': returns.count(),
                    'total_quantity': returns.aggregate(total=Sum('quantity'))['total'] or 0
                }
            })
            
        except Supplier.DoesNotExist:
            return Response(
                {'error': 'Proveedor no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not items:
            return Response(
                {"detail": "Se requiere al menos un item"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        movements_created = []
        total_amount = 0
        
        for item in items:
            try:
                movement = create_purchase(
                    variant_id=item['variant_id'],
                    quantity=item['quantity'],
                    unit_cost=item['unit_cost'],
                    supplier_name=supplier.name,
                    user=request.user
                )
                movements_created.append(movement.id)
                total_amount += item['quantity'] * item['unit_cost']
            except Exception as e:
                return Response(
                    {"detail": f"Error en item {item.get('variant_id')}: {str(e)}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Actualizar datos del proveedor
        supplier.last_purchase_date = now().date()
        supplier.save()
        
        return Response({
            "status": "purchase created",
            "supplier": supplier.name,
            "movements_created": movements_created,
            "total_amount": total_amount
        })

    @action(detail=True, methods=['post'])
    def return_to_supplier(self, request, pk=None):
        """
        Crear devolución a este proveedor
        
        POST /api/suppliers/{id}/return-to-supplier/
        {
            "variant_id": 1,
            "quantity": 2,
            "reason": "Defectuoso"
        }
        """
        supplier = self.get_object()
        
        try:
            movement = create_supplier_return(
                variant_id=request.data['variant_id'],
                quantity=request.data['quantity'],
                reason=request.data['reason'],
                supplier_name=supplier.name,
                user=request.user
            )
            
            return Response({
                "status": "return created",
                "supplier": supplier.name,
                "movement_id": movement.id
            })
            
        except Exception as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def preferred_products(self, request):
        """
        Obtener productos preferidos por proveedores activos
        """
        suppliers = Supplier.objects.filter(is_active=True).prefetch_related('preferred_products')
        
        result = []
        for supplier in suppliers:
            products = [
                {
                    "id": product.id,
                    "name": product.name,
                    "brand": product.brand,
                    "sku": product.sku if hasattr(product, 'sku') else ""
                }
                for product in supplier.preferred_products.all()
            ]
            
            result.append({
                "supplier": {
                    "id": supplier.id,
                    "name": supplier.name,
                    "last_purchase_date": supplier.last_purchase_date
                },
                "preferred_products": products
            })
        
        return Response(result)
