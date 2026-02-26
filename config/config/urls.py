"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from inventory import views, views_home
from drf_spectacular.utils import extend_schema
from inventory.store.views import (
    StoreProductListView,
    StoreProductDetailView,
    StoreBrandingView,
    StoreCustomerRegisterView,
    StoreCustomerLoginView,
    StoreMyOrdersView,
    StoreFeaturedProductsView,
    StoreRelatedProductsView,
    StoreCartValidateView,
    StoreCheckoutView,
    StoreOrderLookupView,
    StoreOrderStatusView,
    StoreOrderPaymentView,
    StoreWompiVerifyPaymentView,
    StoreWompiWebhookView,
    StoreShippingWebhookView,
    StoreWompiHealthView,
    StoreOpsOrderListView,
    StoreOpsManualShipmentView,
    StoreOpsOrderStatusUpdateView,
    StoreOpsSummaryView,
    StoreOpsBrandingView,
)

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    View para obtener el token de acceso usando las credenciales del usuario con extend_schema.
    """
    @extend_schema(
        tags=['Authentication'],
        summary='Obtener token de acceso',
        description='Endpoint para obtener un par de tokens (access y refresh) mediante credenciales de usuario.'
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class CustomTokenRefreshView(TokenRefreshView):
    """
    View para renovar el token de acceso usando el token de refresh con extend_schema.
    """
    @extend_schema(
        tags=['Authentication'],
        summary='Renovar token de acceso',
        description='Endpoint para renovar el token de acceso usando el token de refresh.'
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

router = routers.DefaultRouter()
router.register(
    r"users", 
    views.UserViewSet, 
    basename="users"
)
router.register(
    r"groups", 
    views.GroupViewSet, 
    basename="groups"
)
router.register(
    r"permissions",
    views.PermissionViewSet,
    basename="permissions"
)
router.register(
    r"dashboard", 
    views.DashboardViewSet, 
    basename="dashboard"
)
router.register(
    r"export", 
    views.ExportViewSet,
    basename="export"
)
router.register(
    r"batch", 
    views.BatchOperationsViewSet, 
    basename="batch"
)
router.register(
    r"notifications", 
    views.NotificationViewSet, 
    basename="notifications"
)
router.register(
    r"sales", 
    views.SaleViewSet, 
    basename="sales"
)
router.register(
    r"sale-details", 
    views.SaleDetailViewSet, 
    basename="sale-details"
)
router.register(
    r"sale-returns", 
    views.SaleReturnViewSet, 
    basename="sale-returns"
)
router.register(
    r"purchases", 
    views.PurchaseViewSet, 
    basename="purchases"
)
router.register(
    r"products", 
    views.ProductViewSet, 
    basename="products"
)
router.register(
    r"product-variants", 
    views.ProductVariantViewSet, 
    basename="product-variants"
)
router.register(
    r"product-images", 
    views.ProductImageViewSet, 
    basename="product-images"
)
router.register(
    r"movement-inventory", 
    views.MovementInventoryViewSet, 
    basename="movement-inventory"
)
router.register(
    r"inventory-history", 
    views.InventoryHistoryViewSet, 
    basename="inventory-history"
)
router.register(
    r"inventory-report-daily",
    views.InventoryReportDailyViewSet,
    basename="inventory-report-daily",
)
# router.register(r"audit-logs", views.AuditLogViewSet, basename="audit-logs")
router.register(
    r"inventory-snapshots",
    views.InventorySnapshotViewSet,
    basename="inventory-snapshot",
)
router.register(
    r"inventory-adjustments", 
    views.AdjustmentViewSet, 
    basename="inventory-adjustment"
)
router.register(
    r"suppliers", 
    views.SupplierViewSet, 
    basename="suppliers")
router.register(
    r"supplier-returns", 
    views.SupplierReturnViewSet, 
    basename="supplier-returns"
)

urlpatterns = [
    path("", views_home.HomeView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    # JWT Authentication
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    # API endpoints
    path("api/", include(router.urls)),
    path("api/store/products/", StoreProductListView.as_view(), name="store-products"),
    path("api/store/products/<int:product_id>/", StoreProductDetailView.as_view(), name="store-product-detail"),
    path("api/store/branding/", StoreBrandingView.as_view(), name="store-branding"),
    path("api/store/auth/register/", StoreCustomerRegisterView.as_view(), name="store-customer-register"),
    path("api/store/auth/login/", StoreCustomerLoginView.as_view(), name="store-customer-login"),
    path("api/store/me/orders/", StoreMyOrdersView.as_view(), name="store-my-orders"),
    path("api/store/products/featured/", StoreFeaturedProductsView.as_view(), name="store-featured-products"),
    path("api/store/products/<int:product_id>/related/", StoreRelatedProductsView.as_view(), name="store-related-products"),
    path("api/store/cart/validate/", StoreCartValidateView.as_view(), name="store-cart-validate"),
    path("api/store/checkout/", StoreCheckoutView.as_view(), name="store-checkout"),
    path("api/store/orders/lookup/", StoreOrderLookupView.as_view(), name="store-order-lookup"),
    path("api/store/orders/<int:sale_id>/", StoreOrderStatusView.as_view(), name="store-order-status"),
    path("api/store/orders/<int:sale_id>/pay/", StoreOrderPaymentView.as_view(), name="store-order-pay"),
    path("api/store/orders/<int:sale_id>/wompi/verify/", StoreWompiVerifyPaymentView.as_view(), name="store-order-wompi-verify"),
    path("api/store/wompi/webhook/", StoreWompiWebhookView.as_view(), name="store-wompi-webhook"),
    path("api/store/shipping/webhook/", StoreShippingWebhookView.as_view(), name="store-shipping-webhook"),
    path("api/store/wompi/health/", StoreWompiHealthView.as_view(), name="store-wompi-health"),
    path("api/store/ops/orders/", StoreOpsOrderListView.as_view(), name="store-ops-orders"),
    path("api/store/ops/orders/<int:sale_id>/shipment/manual/", StoreOpsManualShipmentView.as_view(), name="store-ops-order-shipment-manual"),
    path("api/store/ops/orders/<int:sale_id>/status/", StoreOpsOrderStatusUpdateView.as_view(), name="store-ops-order-status"),
    path("api/store/ops/summary/", StoreOpsSummaryView.as_view(), name="store-ops-summary"),
    path("api/store/ops/branding/", StoreOpsBrandingView.as_view(), name="store-ops-branding"),
    path("inventory/close-month/", views.InventoryCloseMonthView.as_view()),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/", 
        SpectacularRedocView.as_view(url_name="schema"), 
        name="redoc"
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
