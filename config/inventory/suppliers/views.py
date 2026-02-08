"""
Views para gestión de proveedores
"""
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Avg, Max, Count
from django.utils.timezone import now
from ..models import Supplier
from ..core.services import create_purchase, create_supplier_return
from .serializers import SupplierSerializer, SupplierSimpleSerializer


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
