"""
Views para gestión de ventas
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count
from ..models import Sale, SaleDetail, MovementInventory, models
from ..core.services import SaleService
from ..core.api_responses import (
    error_response,
    success_response,
    validation_error_payload,
)
from .serializers import (
    SaleCreateSerializer,
    SaleReadSerializer,
    SaleDetailCreateSerializer,
    SaleDetailReadSerializer,
    SaleReturnCreateSerializer,
    SaleReturnSerializer,
)


@extend_schema(tags=["Sales"])
class SaleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de ventas

    - Lectura: Usuarios autenticados con permiso view_sale
    - Creación: Usuarios autenticados con permiso add_sale
    - Actualización: Usuarios autenticados con permiso change_sale
    - Confirmación: Usuarios autenticados con permiso confirm_sale
    """

    queryset = Sale.objects.prefetch_related(
        models.Prefetch('details', queryset=SaleDetail.objects.filter(variant__is_deleted=False))
    ).all()
    permission_classes = [
        permissions.IsAuthenticated,
        permissions.DjangoModelPermissions,
    ]
    filterset_fields = ["status", "is_order"]
    search_fields = ["customer"]
    ordering_fields = ["created_at", "updated_at", "total", "customer"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return SaleReadSerializer
        return SaleCreateSerializer

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """
        Confirma una venta pendiente:
        1. Valida stock disponible
        2. Crea movimientos de inventario
        3. Actualiza estado a 'completed'
        4. Registra en auditoría
        """

        # Verificar permiso específico para confirmar ventas
        if not request.user.has_perm("inventory.confirm_sale"):
            return error_response(
                detail="No tienes permiso para confirmar ventas",
                code="PERMISSION_DENIED",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        try:
            SaleService.confirm_sale(sale_id=pk, user=request.user)
            return success_response(
                detail="Venta confirmada y stock actualizado",
                code="SALE_CONFIRMED",
            )
        except ValidationError as e:
            payload = validation_error_payload(
                e,
                default_detail="No se pudo confirmar la venta",
                default_code="SALE_CONFIRMATION_FAILED",
            )
            is_stock_conflict = any("Stock insuficiente" in msg for msg in payload["errors"])
            http_status = status.HTTP_409_CONFLICT if is_stock_conflict else status.HTTP_400_BAD_REQUEST
            return Response(payload, status=http_status)
        except Sale.DoesNotExist:
            return error_response(
                detail="Venta no encontrada",
                code="SALE_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Cancela una venta pendiente:
        1. Verifica que la venta esté pendiente
        2. Actualiza estado a 'canceled'
        3. Registra en auditoría
        """

        try:
            sale = self.get_object()
            if sale.status != "pending":
                return error_response(
                    detail="Solo se pueden cancelar ventas pendientes",
                    code="INVALID_SALE_STATUS",
                    http_status=status.HTTP_400_BAD_REQUEST,
                )
            
            sale.status = "canceled"
            sale.save()
            
            # Registrar en auditoría
            from ..models import AuditLog
            AuditLog.objects.create(
                action="cancel_sale",
                entity="sale",
                entity_id=sale.id,
                performed_by=request.user.username,
                extra_data={
                    "customer": sale.customer,
                    "total": float(sale.total),
                },
            )
            
            return success_response(
                detail="Venta cancelada",
                code="SALE_CANCELED",
            )
        except Sale.DoesNotExist:
            return error_response(
                detail="Venta no encontrada",
                code="SALE_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return error_response(
                detail=str(e),
                code="SALE_CANCELLATION_FAILED",
                http_status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=["SalesReturns"])
class SaleReturnViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de devoluciones de ventas

    - Lectura: Usuarios autenticados con permiso view_movement_inventory
    - Creación: Usuarios autenticados con permiso add_movement_inventory
    """

    queryset = MovementInventory.objects.filter(
        movement_type=MovementInventory.MovementType.SALE_RETURN
    ).select_related("variant__product", "sale", "sale__customer")

    serializer_class = SaleReturnSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        permissions.DjangoModelPermissions,
    ]

    def get_serializer_class(self):
        if self.action in ["create", "create_sale_return"]:
            return SaleReturnCreateSerializer
        return SaleReturnSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # 1. Filtro por Venta (Usando la nueva relación directa)
        sale_id = self.request.query_params.get(
            "sale"
        ) or self.request.query_params.get("sale_id")
        if sale_id:
            # Filtramos por el campo FK, mucho más rápido que buscar en texto
            queryset = queryset.filter(sale_id=sale_id)

        # 2. Filtro por Producto
        product_id = self.request.query_params.get("product")
        if product_id:
            queryset = queryset.filter(variant__product_id=product_id)

        # 3. Filtro por Fechas
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        try:
            if start_date:
                queryset = queryset.filter(
                    created_at__date__gte=datetime.strptime(
                        start_date, "%Y-%m-%d"
                    ).date()
                )
            if end_date:
                queryset = queryset.filter(
                    created_at__date__lte=datetime.strptime(end_date, "%Y-%m-%d").date()
                )
        except ValueError:
            pass  # Opcionalmente podrías retornar un error 400 aquí

        return queryset

    def create(self, request, *args, **kwargs):
        """Sobrescribimos create para usar el servicio y mantener la lógica de tu app"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Llamamos al Service (encapsulando la lógica de negocio)
            movements = SaleService.create_sale_return(
                sale_id=serializer.validated_data["sale_id"],
                items=serializer.validated_data["items"],
                reason=serializer.validated_data.get("reason", "Devolución de cliente"),
                user=request.user,
            )

            # Si el serializer de entrada tenía razones individuales, las aplicamos
            for i, item_data in enumerate(serializer.validated_data["items"]):
                if item_data.get("reason"):
                    movements[i].observation += f" - Motivo: {item_data['reason']}"
                    movements[i].save(update_fields=["observation"])

            return success_response(
                detail=f"Se crearon {len(movements)} movimientos de devolución",
                code="SALE_RETURN_CREATED",
                http_status=status.HTTP_201_CREATED,
                returns=SaleReturnSerializer(movements, many=True).data,
            )

        except Exception as e:
            return error_response(
                detail=str(e),
                code="SALE_RETURN_CREATE_FAILED",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"])
    def return_stats(self, request):
        """Estadísticas optimizadas"""
        queryset = self.get_queryset()

        stats = queryset.aggregate(total_count=Count("id"), total_qty=Sum("quantity"))

        product_stats = (
            queryset.values("variant__product__name", "variant__product__id")
            .annotate(total_quantity=Sum("quantity"), return_count=Count("id"))
            .order_by("-total_quantity")[:10]
        )  # Top 10

        return Response({"summary": stats, "top_products": product_stats})

    @action(detail=False, methods=["post"], url_path="create-return")
    def create_sale_return(self, request):
        """Crea una devolución y actualiza inventario usando el Service"""
        serializer = SaleReturnCreateSerializer(data=request.data)

        if serializer.is_valid():
            try:
                # Llamamos al servicio con los datos validados
                movements = SaleService.create_sale_return(
                    sale_id=serializer.validated_data["sale_id"],
                    items=serializer.validated_data["items"],
                    reason=serializer.validated_data.get("reason", ""),
                    user=request.user,
                )

                # Devolvemos los movimientos creados usando el serializer de lectura
                return Response(
                    SaleReturnSerializer(movements, many=True).data,
                    status=status.HTTP_201_CREATED,
                )
            except Exception as e:
                return error_response(
                    detail=str(e),
                    code="SALE_RETURN_CREATE_FAILED",
                    http_status=status.HTTP_400_BAD_REQUEST,
                )

        return error_response(
            detail="Datos invalidos para crear devolucion",
            code="VALIDATION_ERROR",
            http_status=status.HTTP_400_BAD_REQUEST,
            errors=[str(serializer.errors)],
        )

    @action(detail=False, methods=["get"], url_path="list-returns")
    def sale_returns(self, request):
        """Consulta las devoluciones existentes de una venta"""
        sale_id = request.query_params.get("sale_id")

        if not sale_id:
            return error_response(
                detail="Se requiere sale_id",
                code="MISSING_SALE_ID",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        # Buscamos los movimientos de tipo SALE_RETURN que mencionen esta venta
        returns = MovementInventory.objects.filter(
            movement_type=MovementInventory.MovementType.SALE_RETURN,
            observation__contains=f"venta #{sale_id}",
        )

        return Response(
            {
                "returns": SaleReturnSerializer(returns, many=True).data,
                "summary": {
                    "total_returns": returns.count(),
                    "total_quantity": returns.aggregate(total=Sum("quantity"))["total"]
                    or 0,
                },
            }
        )


@extend_schema(tags=["SalesDetails"])
class SaleDetailViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de detalles de ventas

    - Solo muestra detalles de ventas pendientes
    """

    serializer_class = SaleDetailCreateSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        permissions.DjangoModelPermissions,
    ]

    def get_queryset(self):
        """Filtra por venta pendiente específica"""
        sale_id = self.kwargs.get("sale_pk")
        if sale_id:
            return SaleDetail.objects.filter(
                sale_id=sale_id, sale__status="pending", quantity__gt=0, variant__is_deleted=False
            ).select_related("sale", "variant", "variant__product")
        return SaleDetail.objects.filter(
            sale__status="pending", quantity__gt=0, variant__is_deleted=False
        ).select_related("sale", "variant", "variant__product")

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return SaleDetailReadSerializer
        return SaleDetailCreateSerializer
