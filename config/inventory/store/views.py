"""
Views publicas para la tienda en linea.
"""

from __future__ import annotations

from decimal import Decimal
import hashlib
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from ..core.api_responses import error_response, success_response
from ..models import AuditLog, Product, ProductImage, ProductVariant, Sale, SaleDetail, StoreBranding
from .serializers import (
    StoreBrandingSerializer,
    StoreBrandingUpdateSerializer,
    StoreCartValidateSerializer,
    StoreCheckoutSerializer,
    StoreCustomerLoginSerializer,
    StoreCustomerRegisterSerializer,
    StoreProductSerializer,
)
from .wompi import WompiError, amount_to_cents, build_checkout_url, extract_event_signature_payload, get_transaction


ORDER_STATUS_META = {
    "pending": {"label": "Pendiente de pago", "stage": 1},
    "paid": {"label": "Pagado", "stage": 2},
    "processing": {"label": "En preparacion", "stage": 3},
    "shipped": {"label": "Enviado", "stage": 4},
    "delivered": {"label": "Entregado", "stage": 5},
    "completed": {"label": "Completado", "stage": 6},
    "canceled": {"label": "Cancelado", "stage": 0},
}

ORDER_TRANSITIONS = {
    "pending": {"paid", "canceled"},
    "paid": {"processing", "canceled"},
    "processing": {"shipped", "canceled"},
    "shipped": {"delivered"},
    "delivered": {"completed"},
    "completed": set(),
    "canceled": set(),
}

DEFAULT_STORE_BRANDING = {
    "store_name": "Golos Store",
    "tagline": "Calzado y estilo para cada paso",
    "logo_url": "",
    "hero_title": "Descubre tu siguiente par favorito",
    "hero_subtitle": "Compra facil, segura y con envio rapido en Colombia.",
}

CUSTOMER_GROUP_NAME = "Customers"


def _store_products_queryset():
    available_variants = (
        ProductVariant.objects.filter(
            product=OuterRef("pk"),
            active=True,
            is_deleted=False,
        )
        .annotate(current_stock=Coalesce(Sum("movements__quantity"), 0))
        .filter(current_stock__gt=0)
    )

    variants_prefetch = Prefetch(
        "variants",
        queryset=(
            ProductVariant.objects.filter(active=True, is_deleted=False)
            .annotate(current_stock=Coalesce(Sum("movements__quantity"), 0))
            .filter(current_stock__gt=0)
            .order_by("id")
        ),
        to_attr="store_variants",
    )
    images_prefetch = Prefetch(
        "images",
        queryset=ProductImage.objects.select_related("variant").order_by("-is_primary", "id"),
        to_attr="store_images",
    )

    return (
        Product.objects.filter(active=True)
        .annotate(has_available_variants=Exists(available_variants))
        .filter(has_available_variants=True)
        .prefetch_related(variants_prefetch, images_prefetch)
        .order_by("name")
    )


def _parse_positive_int(value: str | None, default: int, max_value: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    if parsed < 1:
        return default
    return min(parsed, max_value)


def _serialize_sale_items(sale: Sale) -> list[dict]:
    details = sale.details.select_related("variant__product").all()
    return [
        {
            "variant_id": detail.variant_id,
            "product_name": detail.variant.product.name,
            "variant_info": f"{detail.variant.get_gender_display()} - {detail.variant.color} - {detail.variant.size}",
            "quantity": detail.quantity,
            "unit_price": str(detail.price),
            "subtotal": str(detail.subtotal),
        }
        for detail in details
    ]


def _status_detail(status_code: str) -> dict:
    meta = ORDER_STATUS_META.get(status_code, {"label": status_code, "stage": 0})
    return {
        "code": status_code,
        "label": meta["label"],
        "stage": meta["stage"],
    }


def _order_timeline(sale: Sale) -> list[dict]:
    timeline = [
        {
            "code": "created",
            "label": "Pedido creado",
            "at": sale.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
    ]

    if sale.paid_at:
        timeline.append({"code": "paid", "label": "Pago confirmado", "at": sale.paid_at.strftime("%Y-%m-%d %H:%M:%S")})
    if sale.confirmed_at:
        timeline.append(
            {"code": "processing", "label": "Pedido en preparacion", "at": sale.confirmed_at.strftime("%Y-%m-%d %H:%M:%S")}
        )
    if sale.shipped_at:
        timeline.append({"code": "shipped", "label": "Pedido enviado", "at": sale.shipped_at.strftime("%Y-%m-%d %H:%M:%S")})
    if sale.delivered_at:
        timeline.append(
            {"code": "delivered", "label": "Pedido entregado", "at": sale.delivered_at.strftime("%Y-%m-%d %H:%M:%S")}
        )
    if sale.canceled_at:
        timeline.append({"code": "canceled", "label": "Pedido cancelado", "at": sale.canceled_at.strftime("%Y-%m-%d %H:%M:%S")})

    return timeline


def _serialize_store_order(sale: Sale) -> dict:
    return {
        "sale_id": sale.id,
        "status": sale.status,
        "status_detail": _status_detail(sale.status),
        "payment_status": sale.payment_status,
        "payment_method": sale.payment_method,
        "payment_reference": sale.payment_reference,
        "is_order": sale.is_order,
        "total": str(sale.total),
        "created_at": sale.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": sale.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        "items": _serialize_sale_items(sale),
        "timeline": _order_timeline(sale),
    }


def _serialize_store_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "groups": list(user.groups.values_list("name", flat=True)),
    }


def _get_store_branding_instance() -> StoreBranding:
    branding = StoreBranding.objects.order_by("id").first()
    if branding:
        return branding
    return StoreBranding.objects.create(**DEFAULT_STORE_BRANDING)


def _ensure_store_wompi_ready() -> str | None:
    if not settings.WOMPI_PUBLIC_KEY or not settings.WOMPI_INTEGRITY_SECRET:
        return "Wompi no esta configurado en el servidor"
    return None


def _apply_wompi_transaction_to_sale(sale: Sale, transaction_data: dict, source: str = "wompi_verify") -> None:
    status_map = {
        "APPROVED": ("paid", "paid"),
        "PENDING": ("pending", "pending"),
        "DECLINED": ("pending", "failed"),
        "VOIDED": ("canceled", "failed"),
        "ERROR": ("pending", "failed"),
    }

    wompi_status = (transaction_data.get("status") or "").upper()
    order_status, payment_status = status_map.get(wompi_status, (sale.status, sale.payment_status))
    now = timezone.now()

    fields_to_update = ["updated_at"]
    if sale.status != order_status:
        sale.status = order_status
        fields_to_update.append("status")
    if sale.payment_status != payment_status:
        sale.payment_status = payment_status
        fields_to_update.append("payment_status")

    method = (
        transaction_data.get("payment_method_type")
        or transaction_data.get("payment_method", {}).get("type")
        or sale.payment_method
    )
    if method and sale.payment_method != method:
        sale.payment_method = method
        fields_to_update.append("payment_method")

    if wompi_status == "APPROVED" and not sale.paid_at:
        sale.paid_at = now
        fields_to_update.append("paid_at")
    if wompi_status == "VOIDED" and not sale.canceled_at:
        sale.canceled_at = now
        fields_to_update.append("canceled_at")

    sale.save(update_fields=list(dict.fromkeys(fields_to_update)))

    AuditLog.objects.create(
        action="wompi_transaction_sync",
        entity="sale",
        entity_id=sale.id,
        performed_by="store_api",
        extra_data={
            "source": source,
            "wompi_transaction_id": transaction_data.get("id"),
            "wompi_status": wompi_status,
            "payment_status": sale.payment_status,
            "order_status": sale.status,
        },
    )


@extend_schema(tags=["Store"])
class StoreProductListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        queryset = _store_products_queryset()

        q = request.query_params.get("q")
        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(brand__icontains=q))

        brand = request.query_params.get("brand")
        if brand:
            queryset = queryset.filter(brand__iexact=brand)

        product_type = request.query_params.get("product_type")
        if product_type:
            queryset = queryset.filter(product_type=product_type)

        ordering = request.query_params.get("ordering", "name")
        ordering_map = {
            "name": "name",
            "-name": "-name",
            "brand": "brand",
            "-brand": "-brand",
            "newest": "-created_at",
            "oldest": "created_at",
        }
        queryset = queryset.order_by(ordering_map.get(ordering, "name"))

        total_count = queryset.count()
        page = _parse_positive_int(request.query_params.get("page"), default=1, max_value=10_000)
        page_size = _parse_positive_int(request.query_params.get("page_size"), default=12, max_value=48)
        offset = (page - 1) * page_size
        products = list(queryset[offset : offset + page_size])
        serializer = StoreProductSerializer(products, many=True)

        return success_response(
            detail="Catalogo de tienda obtenido correctamente",
            code="STORE_PRODUCTS_OK",
            count=total_count,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total_count,
            products=serializer.data,
        )


@extend_schema(tags=["Store"])
class StoreProductDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id: int):
        product = _store_products_queryset().filter(id=product_id).first()
        if not product:
            return error_response(
                detail="Producto no disponible",
                code="STORE_PRODUCT_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StoreProductSerializer(product)
        return success_response(
            detail="Producto de tienda obtenido correctamente",
            code="STORE_PRODUCT_OK",
            product=serializer.data,
        )


@extend_schema(tags=["Store"])
class StoreBrandingView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        branding = _get_store_branding_instance()
        return success_response(
            detail="Branding de tienda obtenido correctamente",
            code="STORE_BRANDING_OK",
            branding=StoreBrandingSerializer(branding).data,
        )


@extend_schema(tags=["StoreAuth"])
class StoreCustomerRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = StoreCustomerRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                detail="No se pudo registrar el cliente",
                code="STORE_CUSTOMER_REGISTER_FAILED",
                http_status=status.HTTP_400_BAD_REQUEST,
                errors=[str(serializer.errors)],
            )

        data = serializer.validated_data
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            is_staff=False,
        )

        customers_group, _ = Group.objects.get_or_create(name=CUSTOMER_GROUP_NAME)
        user.groups.add(customers_group)

        refresh = RefreshToken.for_user(user)
        return success_response(
            detail="Cliente registrado correctamente",
            code="STORE_CUSTOMER_REGISTERED",
            http_status=status.HTTP_201_CREATED,
            access=str(refresh.access_token),
            refresh=str(refresh),
            user=_serialize_store_user(user),
        )


@extend_schema(tags=["StoreAuth"])
class StoreCustomerLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = StoreCustomerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                detail="No se pudo iniciar sesion",
                code="STORE_CUSTOMER_LOGIN_FAILED",
                http_status=status.HTTP_400_BAD_REQUEST,
                errors=[str(serializer.errors)],
            )

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return success_response(
            detail="Sesion iniciada correctamente",
            code="STORE_CUSTOMER_LOGIN_OK",
            access=str(refresh.access_token),
            refresh=str(refresh),
            user=_serialize_store_user(user),
        )


@extend_schema(tags=["StoreAuth"])
class StoreMyOrdersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = (
            Sale.objects.filter(created_by=request.user.username, is_order=True)
            .prefetch_related("details__variant__product")
            .order_by("-created_at")
        )
        orders = [_serialize_store_order(sale) for sale in queryset]
        return success_response(
            detail="Pedidos del cliente obtenidos correctamente",
            code="STORE_MY_ORDERS_OK",
            count=len(orders),
            orders=orders,
        )


@extend_schema(tags=["StoreOps"])
class StoreOpsBrandingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        branding = _get_store_branding_instance()
        return success_response(
            detail="Branding de tienda obtenido correctamente",
            code="STORE_OPS_BRANDING_OK",
            branding=StoreBrandingSerializer(branding).data,
        )

    def patch(self, request):
        if not request.user.has_perm("inventory.change_sale"):
            return error_response(
                detail="No tienes permisos para editar branding",
                code="PERMISSION_DENIED",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        branding = _get_store_branding_instance()
        serializer = StoreBrandingUpdateSerializer(instance=branding, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(
                detail="No se pudo actualizar branding",
                code="STORE_OPS_BRANDING_UPDATE_FAILED",
                http_status=status.HTTP_400_BAD_REQUEST,
                errors=[str(serializer.errors)],
            )

        updated = serializer.save(updated_by=request.user.username)
        return success_response(
            detail="Branding actualizado correctamente",
            code="STORE_OPS_BRANDING_UPDATED",
            branding=StoreBrandingSerializer(updated).data,
        )


@extend_schema(tags=["Store"])
class StoreFeaturedProductsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        limit = _parse_positive_int(request.query_params.get("limit"), default=8, max_value=24)
        products = list(_store_products_queryset().order_by("-created_at")[:limit])
        serializer = StoreProductSerializer(products, many=True)
        return success_response(
            detail="Productos destacados obtenidos correctamente",
            code="STORE_FEATURED_PRODUCTS_OK",
            count=len(serializer.data),
            products=serializer.data,
        )


@extend_schema(tags=["Store"])
class StoreRelatedProductsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id: int):
        base_product = Product.objects.filter(id=product_id, active=True).first()
        if not base_product:
            return error_response(
                detail="Producto no disponible",
                code="STORE_PRODUCT_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        limit = _parse_positive_int(request.query_params.get("limit"), default=6, max_value=24)
        related = _store_products_queryset().filter(
            Q(brand__iexact=base_product.brand) | Q(product_type=base_product.product_type)
        ).exclude(id=base_product.id)[:limit]
        serializer = StoreProductSerializer(list(related), many=True)

        return success_response(
            detail="Productos relacionados obtenidos correctamente",
            code="STORE_RELATED_PRODUCTS_OK",
            base_product_id=base_product.id,
            count=len(serializer.data),
            products=serializer.data,
        )


@extend_schema(tags=["Store"])
class StoreCartValidateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = StoreCartValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                detail="No se pudo validar el carrito",
                code="STORE_CART_VALIDATION_FAILED",
                http_status=status.HTTP_400_BAD_REQUEST,
                errors=[str(serializer.errors)],
            )

        normalized_items = serializer.validated_data["items"]
        items = [
            {
                "variant_id": item["variant"].id,
                "product_name": item["variant"].product.name,
                "variant_info": f"{item['variant'].get_gender_display()} - {item['variant'].color} - {item['variant'].size}",
                "quantity": item["quantity"],
                "unit_price": str(item["unit_price"]),
                "subtotal": str(item["subtotal"]),
                "available_stock": item["available_stock"],
            }
            for item in normalized_items
        ]
        total = sum((item["subtotal"] for item in normalized_items), start=Decimal("0.00"))

        return success_response(
            detail="Carrito validado correctamente",
            code="STORE_CART_VALID",
            items=items,
            total=str(total),
        )


@extend_schema(tags=["Store"])
class StoreCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        payload = dict(request.data)
        fallback_name = (
            f"{request.user.first_name} {request.user.last_name}".strip()
            or request.user.username
        )
        fallback_contact = (request.user.email or request.user.username or "").strip()
        payload["customer_name"] = (payload.get("customer_name") or "").strip() or fallback_name
        payload["customer_contact"] = (payload.get("customer_contact") or "").strip() or fallback_contact

        serializer = StoreCheckoutSerializer(data=payload)
        if not serializer.is_valid():
            return error_response(
                detail="No se pudo crear el checkout",
                code="STORE_CHECKOUT_FAILED",
                http_status=status.HTTP_400_BAD_REQUEST,
                errors=[str(serializer.errors)],
            )

        validated = serializer.validated_data
        customer = validated["customer_name"]
        contact = validated.get("customer_contact")
        if contact:
            customer = f"{customer} ({contact})"

        items = validated["items"]
        total = sum((item["subtotal"] for item in items), start=Decimal("0.00"))

        created_by = request.user.username

        sale = Sale.objects.create(
            customer=customer,
            created_by=created_by,
            is_order=validated.get("is_order", True),
            total=total,
            status="pending",
            payment_status="unpaid",
            payment_reference=f"ORD-{uuid4().hex[:12].upper()}",
        )

        sale_details = [
            SaleDetail(
                sale=sale,
                variant=item["variant"],
                quantity=item["quantity"],
                price=item["unit_price"],
                subtotal=item["subtotal"],
            )
            for item in items
        ]
        SaleDetail.objects.bulk_create(sale_details)

        return success_response(
            detail="Pedido creado correctamente",
            code="STORE_CHECKOUT_CREATED",
            http_status=status.HTTP_201_CREATED,
            order={
                "sale_id": sale.id,
                "status": sale.status,
                "is_order": sale.is_order,
                "total": str(total),
                "items_count": len(sale_details),
            },
        )


@extend_schema(tags=["Store"])
class StoreOrderStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, sale_id: int):
        contact = (request.query_params.get("customer_contact") or "").strip()
        is_authenticated_customer = request.user.is_authenticated
        if not contact and not is_authenticated_customer:
            return error_response(
                detail="customer_contact es requerido",
                code="STORE_ORDER_CONTACT_REQUIRED",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        sale_qs = Sale.objects.prefetch_related("details__variant__product").filter(id=sale_id)
        if request.user.is_authenticated:
            sale_qs = sale_qs.filter(Q(created_by="store_api") | Q(created_by=request.user.username))
        else:
            sale_qs = sale_qs.filter(created_by="store_api")
        sale = sale_qs.first()
        if not sale:
            return error_response(
                detail="Pedido no encontrado",
                code="STORE_ORDER_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        owner_match = request.user.is_authenticated and sale.created_by == request.user.username
        if not owner_match and contact not in sale.customer:
            return error_response(
                detail="No autorizado para consultar este pedido",
                code="STORE_ORDER_ACCESS_DENIED",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        return success_response(
            detail="Estado del pedido obtenido correctamente",
            code="STORE_ORDER_STATUS_OK",
            order=_serialize_store_order(sale),
        )


@extend_schema(tags=["Store"])
class StoreOrderLookupView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        sale_id_raw = (request.query_params.get("sale_id") or "").strip()
        customer_query = (request.query_params.get("customer") or "").strip()
        contact_hint = (request.query_params.get("customer_contact") or "").strip()

        if not sale_id_raw and not customer_query:
            return error_response(
                detail="Debes enviar sale_id o customer",
                code="STORE_ORDER_LOOKUP_MISSING_FILTER",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        if customer_query and not request.user.is_authenticated and len(contact_hint) < 4:
            return error_response(
                detail="Para buscar por cliente debes enviar customer_contact (minimo 4 caracteres)",
                code="STORE_ORDER_LOOKUP_CONTACT_REQUIRED",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Sale.objects.prefetch_related("details__variant__product").filter(is_order=True)
        if request.user.is_authenticated:
            queryset = queryset.filter(Q(created_by="store_api") | Q(created_by=request.user.username))
        else:
            queryset = queryset.filter(created_by="store_api")

        if sale_id_raw:
            try:
                sale_id = int(sale_id_raw)
            except ValueError:
                return error_response(
                    detail="sale_id invalido",
                    code="STORE_ORDER_LOOKUP_INVALID_SALE_ID",
                    http_status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(id=sale_id)

        if customer_query:
            queryset = queryset.filter(customer__icontains=customer_query)
        if contact_hint:
            queryset = queryset.filter(customer__icontains=contact_hint)

        orders = list(queryset.order_by("-created_at")[:20])
        if not orders:
            return error_response(
                detail="No se encontraron pedidos con ese criterio",
                code="STORE_ORDER_LOOKUP_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        return success_response(
            detail="Pedidos encontrados correctamente",
            code="STORE_ORDER_LOOKUP_OK",
            count=len(orders),
            orders=[_serialize_store_order(sale) for sale in orders],
        )


@extend_schema(tags=["Store"])
class StoreOrderPaymentView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, sale_id: int):
        contact = (request.data.get("customer_contact") or "").strip()
        payment_method = (request.data.get("payment_method") or "CARD").strip().upper()

        if not contact and not request.user.is_authenticated:
            return error_response(
                detail="customer_contact es requerido",
                code="STORE_ORDER_CONTACT_REQUIRED",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        sale_qs = Sale.objects.select_for_update().filter(id=sale_id)
        if request.user.is_authenticated:
            sale_qs = sale_qs.filter(Q(created_by="store_api") | Q(created_by=request.user.username))
        else:
            sale_qs = sale_qs.filter(created_by="store_api")
        sale = sale_qs.first()
        if not sale:
            return error_response(
                detail="Pedido no encontrado",
                code="STORE_ORDER_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        owner_match = request.user.is_authenticated and sale.created_by == request.user.username
        if not owner_match and contact not in sale.customer:
            return error_response(
                detail="No autorizado para pagar este pedido",
                code="STORE_ORDER_ACCESS_DENIED",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        wompi_error = _ensure_store_wompi_ready()
        if wompi_error:
            return error_response(
                detail=wompi_error,
                code="STORE_WOMPI_NOT_CONFIGURED",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if sale.status in {"paid", "processing", "shipped", "delivered", "completed"} and sale.payment_status == "paid":
            return error_response(
                detail="Este pedido ya tiene pago confirmado",
                code="STORE_ORDER_ALREADY_PAID",
                http_status=status.HTTP_409_CONFLICT,
            )
        if sale.status == "canceled":
            return error_response(
                detail="No se puede pagar un pedido cancelado",
                code="STORE_ORDER_CANCELED",
                http_status=status.HTTP_409_CONFLICT,
            )

        if not sale.payment_reference:
            sale.payment_reference = f"ORD-{uuid4().hex[:12].upper()}"

        sale.payment_method = payment_method
        if sale.payment_status == "unpaid":
            sale.payment_status = "pending"
        sale.save(update_fields=["payment_reference", "payment_method", "payment_status", "updated_at"])

        AuditLog.objects.create(
            action="store_order_payment_checkout_init",
            entity="sale",
            entity_id=sale.id,
            performed_by="store_api",
            extra_data={
                "payment_method": payment_method,
                "payment_reference": sale.payment_reference,
                "total": float(sale.total),
            },
        )

        amount_in_cents = amount_to_cents(str(sale.total))
        checkout_url = build_checkout_url(
            reference=sale.payment_reference,
            amount_in_cents=amount_in_cents,
            redirect_url=f"{settings.WOMPI_REDIRECT_URL}?sale_id={sale.id}&customer_contact={contact}",
            currency="COP",
        )

        return success_response(
            detail="Checkout de pago generado correctamente",
            code="STORE_ORDER_PAYMENT_CHECKOUT_READY",
            payment={
                "reference": sale.payment_reference,
                "method": payment_method,
                "status": sale.payment_status,
                "paid_at": sale.paid_at.strftime("%Y-%m-%d %H:%M:%S") if sale.paid_at else None,
                "checkout_url": checkout_url,
            },
            order=_serialize_store_order(sale),
        )


@extend_schema(tags=["Store"])
class StoreWompiVerifyPaymentView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, sale_id: int):
        contact = (request.data.get("customer_contact") or "").strip()
        transaction_id = (request.data.get("transaction_id") or "").strip()

        if (not contact and not request.user.is_authenticated) or not transaction_id:
            return error_response(
                detail="customer_contact y transaction_id son requeridos",
                code="STORE_WOMPI_VERIFY_MISSING_FIELDS",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        sale_qs = Sale.objects.select_for_update().filter(id=sale_id)
        if request.user.is_authenticated:
            sale_qs = sale_qs.filter(Q(created_by="store_api") | Q(created_by=request.user.username))
        else:
            sale_qs = sale_qs.filter(created_by="store_api")
        sale = sale_qs.first()
        if not sale:
            return error_response(
                detail="Pedido no encontrado",
                code="STORE_ORDER_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        owner_match = request.user.is_authenticated and sale.created_by == request.user.username
        if not owner_match and contact not in sale.customer:
            return error_response(
                detail="No autorizado para consultar este pedido",
                code="STORE_ORDER_ACCESS_DENIED",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        try:
            payload = get_transaction(transaction_id)
        except WompiError as exc:
            return error_response(
                detail=f"No se pudo consultar Wompi: {exc}",
                code="STORE_WOMPI_VERIFY_FAILED",
                http_status=status.HTTP_502_BAD_GATEWAY,
            )

        transaction_data = payload.get("data") or {}
        reference = transaction_data.get("reference")
        if reference != sale.payment_reference:
            return error_response(
                detail="La transaccion no corresponde a esta orden",
                code="STORE_WOMPI_REFERENCE_MISMATCH",
                http_status=status.HTTP_409_CONFLICT,
            )

        _apply_wompi_transaction_to_sale(sale, transaction_data, source="wompi_verify")

        return success_response(
            detail="Pago sincronizado correctamente",
            code="STORE_WOMPI_PAYMENT_SYNCED",
            transaction={
                "id": transaction_data.get("id"),
                "status": transaction_data.get("status"),
                "reference": transaction_data.get("reference"),
            },
            order=_serialize_store_order(sale),
        )


@extend_schema(tags=["Store"])
class StoreWompiWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        event = request.data
        data = event.get("data") or {}
        signature = event.get("signature") or {}

        if not settings.WOMPI_EVENTS_SECRET:
            return error_response(
                detail="Wompi webhook no configurado",
                code="STORE_WOMPI_WEBHOOK_NOT_CONFIGURED",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        properties = signature.get("properties") or []
        provided_checksum = (signature.get("checksum") or "").lower()
        payload = extract_event_signature_payload(data, properties)
        calculated_checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest().lower()

        if not provided_checksum or provided_checksum != calculated_checksum:
            return error_response(
                detail="Firma de webhook invalida",
                code="STORE_WOMPI_WEBHOOK_INVALID_SIGNATURE",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        transaction_data = (data.get("transaction") or {}).get("data") or {}
        reference = transaction_data.get("reference")
        if not reference:
            return success_response(
                detail="Webhook recibido sin referencia util",
                code="STORE_WOMPI_WEBHOOK_IGNORED",
            )

        sale = Sale.objects.select_for_update().filter(is_order=True, payment_reference=reference).first()
        if not sale:
            return success_response(
                detail="Webhook sin orden asociada",
                code="STORE_WOMPI_WEBHOOK_NOT_MATCHED",
            )

        _apply_wompi_transaction_to_sale(sale, transaction_data, source="wompi_webhook")

        return success_response(
            detail="Webhook procesado correctamente",
            code="STORE_WOMPI_WEBHOOK_OK",
            order_id=sale.id,
            payment_status=sale.payment_status,
            status=sale.status,
        )


@extend_schema(tags=["Store"])
class StoreWompiHealthView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        required = {
            "WOMPI_PUBLIC_KEY": settings.WOMPI_PUBLIC_KEY,
            "WOMPI_INTEGRITY_SECRET": settings.WOMPI_INTEGRITY_SECRET,
            "WOMPI_EVENTS_SECRET": settings.WOMPI_EVENTS_SECRET,
            "WOMPI_REDIRECT_URL": settings.WOMPI_REDIRECT_URL,
        }
        missing = [key for key, value in required.items() if not value]
        configured = len(missing) == 0

        env = "production" if "production" in settings.WOMPI_API_BASE_URL else "sandbox"
        return success_response(
            detail="Estado de configuracion de Wompi obtenido correctamente",
            code="STORE_WOMPI_HEALTH_OK",
            configured=configured,
            environment=env,
            api_base_url=settings.WOMPI_API_BASE_URL,
            checkout_base_url=settings.WOMPI_CHECKOUT_BASE_URL,
            missing=missing,
        )


@extend_schema(tags=["StoreOps"])
class StoreOpsOrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Sale.objects.filter(is_order=True).order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(customer__icontains=search)

        total_count = queryset.count()
        page = _parse_positive_int(request.query_params.get("page"), default=1, max_value=10_000)
        page_size = _parse_positive_int(request.query_params.get("page_size"), default=20, max_value=100)
        offset = (page - 1) * page_size
        sales = list(queryset[offset : offset + page_size].prefetch_related("details__variant__product"))

        return success_response(
            detail="Ordenes de tienda obtenidas correctamente",
            code="STORE_OPS_ORDERS_OK",
            count=total_count,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total_count,
            orders=[_serialize_store_order(sale) for sale in sales],
        )


@extend_schema(tags=["StoreOps"])
class StoreOpsOrderStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def patch(self, request, sale_id: int):
        if not request.user.has_perm("inventory.change_sale"):
            return error_response(
                detail="No tienes permisos para actualizar ordenes",
                code="PERMISSION_DENIED",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        next_status = (request.data.get("status") or "").strip().lower()
        note = (request.data.get("note") or "").strip()

        if next_status not in ORDER_STATUS_META:
            return error_response(
                detail="Estado de orden invalido",
                code="STORE_OPS_INVALID_STATUS",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        sale = Sale.objects.select_for_update().filter(id=sale_id, is_order=True).first()
        if not sale:
            return error_response(
                detail="Orden no encontrada",
                code="STORE_OPS_ORDER_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        allowed_transitions = ORDER_TRANSITIONS.get(sale.status, set())
        if next_status not in allowed_transitions:
            return error_response(
                detail=f"No se puede pasar de {sale.status} a {next_status}",
                code="STORE_OPS_INVALID_TRANSITION",
                http_status=status.HTTP_409_CONFLICT,
            )

        now = timezone.now()
        sale.status = next_status
        if note:
            sale.status_notes = note

        fields_to_update = ["status", "status_notes", "updated_at"]

        if next_status == "paid":
            sale.payment_status = "paid"
            if not sale.paid_at:
                sale.paid_at = now
            fields_to_update.extend(["payment_status", "paid_at"])
        if next_status == "processing":
            sale.confirmed_at = now
            fields_to_update.append("confirmed_at")
        if next_status == "shipped":
            sale.shipped_at = now
            fields_to_update.append("shipped_at")
        if next_status == "delivered":
            sale.delivered_at = now
            fields_to_update.append("delivered_at")
        if next_status == "canceled":
            sale.canceled_at = now
            fields_to_update.append("canceled_at")

        sale.save(update_fields=list(dict.fromkeys(fields_to_update)))

        AuditLog.objects.create(
            action="store_order_status_update",
            entity="sale",
            entity_id=sale.id,
            performed_by=request.user.username,
            extra_data={
                "status": next_status,
                "note": note,
            },
        )

        return success_response(
            detail="Estado de la orden actualizado correctamente",
            code="STORE_OPS_ORDER_STATUS_UPDATED",
            order=_serialize_store_order(sale),
        )


@extend_schema(tags=["StoreOps"])
class StoreOpsSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = Sale.objects.filter(is_order=True)
        return success_response(
            detail="Resumen operativo obtenido correctamente",
            code="STORE_OPS_SUMMARY_OK",
            summary={
                "total_orders": queryset.count(),
                "pending": queryset.filter(status="pending").count(),
                "paid": queryset.filter(status="paid").count(),
                "processing": queryset.filter(status="processing").count(),
                "shipped": queryset.filter(status="shipped").count(),
                "delivered": queryset.filter(status="delivered").count(),
                "canceled": queryset.filter(status="canceled").count(),
            },
        )
