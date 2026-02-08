"""
Views para gestión de inventario
"""
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from ..models import MovementInventory, InventorySnapshot
from ..core.services import daily_inventory_summary, create_adjustment
from .serializers import (
    MovementInventorySerializer,
    InventoryHistorySerializer,
    DailyInventorySummarySerializer,
    InventorySnapshotSerializer,
)

@extend_schema(tags=['Inventory'])
class MovementInventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consulta de movimientos de inventario (SOLO LECTURA)
    
    - Solo permite consultar movimientos existentes
    - NO permite crear movimientos manuales
    - Los movimientos se crean a través de servicios específicos:
      * Compras: create_purchase()
      * Ventas: confirm_sale() (automático)
      * Devoluciones: create_sale_return()
      * Ajustes: AdjustmentViewSet (controlado)
    """
    queryset = MovementInventory.objects.all().select_related(
        'variant', 'variant__product'
    )
    serializer_class = MovementInventorySerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


@extend_schema(tags=['InventoryHistory'])
class InventoryHistoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para historial de inventario (solo lectura)
    ViewSet de solo lectura para historial de inventario
    
    - Solo lectura para usuarios autenticados
    """
    serializer_class = InventoryHistorySerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def get_queryset(self):
        """
        Filtrado avanzado del historial:
        - ?product=3: Historial de un producto
        - ?variant=12: Historial de una variante
        - ?type=purchase: Tipo específico de movimiento
        - ?page=2: Paginación
        """
        qs = MovementInventory.objects.select_related(
            "variant", "variant__product"
        ).order_by('-created_at')

        # Filtros
        product_id = self.request.query_params.get("product")
        variant_id = self.request.query_params.get("variant")
        movement_type = self.request.query_params.get("type")

        if product_id:
            qs = qs.filter(variant__product_id=product_id)
        if variant_id:
            qs = qs.filter(variant_id=variant_id)
        if movement_type:
            qs = qs.filter(movement_type=movement_type)

        return qs
        
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema(tags=['InventoryReportDaily'])
class InventoryReportDailyViewSet(viewsets.ViewSet):
    """
    Reporte diario de inventario 
    (Solo Admin y Managers)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        start = request.query_params.get("start")
        end = request.query_params.get("end")

        data = daily_inventory_summary(start, end)
        serializer = DailyInventorySummarySerializer(data, many=True)
        return Response(serializer.data)


@extend_schema(tags=['InventorySnapshots'])
class InventorySnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Consulta de snapshots mensuales de inventario
    (Solo Admin y Managers)
    """
    queryset = InventorySnapshot.objects.select_related(
        "variant",
        "variant__product"
    ).order_by("-month")

    serializer_class = InventorySnapshotSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    
    # Tags para documentación Swagger
    tags = ['Inventory']

    def get_queryset(self):
        """
        Filtros disponibles:
        - ?month=2026-01-01
        - ?product=3
        - ?variant=12
        """
        qs = super().get_queryset()

        month = self.request.query_params.get("month")
        product_id = self.request.query_params.get("product")
        variant_id = self.request.query_params.get("variant")

        if month:
            qs = qs.filter(month=month)
        if product_id:
            qs = qs.filter(variant__product_id=product_id)
        if variant_id:
            qs = qs.filter(variant_id=variant_id)

        return qs


@extend_schema(tags=['InventoryCloseMonth'])
class InventoryCloseMonthView(APIView):
    """
    Cierre mensual de inventario
    (Solo Admin y Managers)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        month = request.data.get("month")  # "2026-01-01"
        if not month:
            raise ValidationError("month es requerido")

        close_inventory_month(
            month=month,
            user=request.user
        )

        return Response({"status": "month closed"})


@extend_schema(tags=['InventoryAdjustments'])
class AdjustmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para ajustes manuales de inventario (CONTROLADO)
    
    - Permite crear ajustes manuales con motivo obligatorio
    - Solo usuarios con permisos especiales pueden usarlo
    - Genera movimientos tipo 'adjustment'
    - Auditoría completa de cada ajuste
    """
    serializer_class = MovementInventorySerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    
    # Tags para documentación Swagger
    tags = ['Inventory']

    def get_queryset(self):
        """Solo mostrar movimientos de tipo ajuste"""
        return MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.ADJUSTMENT
        ).select_related('variant', 'variant__product')

    def perform_create(self, serializer):
        """Crear ajuste usando el servicio específico"""
        
        
        variant_id = serializer.validated_data['variant'].id
        quantity = serializer.validated_data['quantity']
        reason = serializer.validated_data.get('observation', '')
        
        # Usar el servicio para crear el ajuste
        create_adjustment(
            variant_id=variant_id,
            quantity=quantity,
            reason=reason,
            user=self.request.user
        )