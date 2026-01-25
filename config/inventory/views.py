from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    UserSerializer,
    SaleCreateSerializer,
    SaleDetailCreateSerializer,
    ProductSerializer,
    ProductVariantSerializer,
    ProductImageSerializer,
    MovementInventorySerializer,
    EmptySerializer,
)
from .management import UserCreateSerializer, UserManagementSerializer, GroupSerializer
from django.contrib.auth.models import User, Group
from .models import (
    Sale,
    SaleDetail,
    Product,
    ProductVariant,
    ProductImage,
    MovementInventory,
)
from .services import confirm_sale
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from .permissions import (
    IsAdminOrReadOnly,
    IsSalesUserOrAdmin,
    IsInventoryUserOrAdmin,
    CanConfirmSales,
)

# Create your views here.


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserManagementSerializer


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAdminOrReadOnly]


class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleCreateSerializer
    permission_classes = [IsSalesUserOrAdmin, CanConfirmSales]

    @action(detail=True, methods=["post"], serializer_class=EmptySerializer)
    def confirm(self, request, pk=None):
        # pk es usado internamente por get_object() para obtener la venta
        sale = self.get_object()
        try:
            confirm_sale(sale_id=sale.id, user=request.user)
        except ValidationError as e:
            raise DRFValidationError(e.message)

        return Response({"status": "sale confirmed"})


class SaleDetailViewSet(viewsets.ModelViewSet):
    serializer_class = SaleDetailCreateSerializer
    permission_classes = [IsSalesUserOrAdmin]

    # obtener detalles de una venta pendiente por id
    def get_queryset(self):
        sale_id = self.request.query_params.get("sale")

        # si no hay id de venta, retornar vacío
        if not sale_id:
            return SaleDetail.objects.none()

        # filtrar por venta pendiente y cantidad mayor a 0
        return SaleDetail.objects.filter(
            sale_id=sale_id, sale__status="pending", quantity__gt=0
        )


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer
    permission_classes = [IsInventoryUserOrAdmin]


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsInventoryUserOrAdmin]


class MovementInventoryViewSet(viewsets.ModelViewSet):
    queryset = MovementInventory.objects.all()
    serializer_class = MovementInventorySerializer
    permission_classes = [IsInventoryUserOrAdmin]
