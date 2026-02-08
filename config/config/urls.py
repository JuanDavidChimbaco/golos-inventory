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
from inventory import views
from inventory.views_home import HomeView
from inventory.views import InventoryCloseMonthView

router = routers.DefaultRouter()
router.register(r"users", views.UserViewSet, basename="users")
router.register(r"groups", views.GroupViewSet, basename="groups")
router.register(r"dashboard", views.DashboardViewSet, basename="dashboard")
router.register(r"sales", views.SaleViewSet, basename="sales")
router.register(r"sale-details", views.SaleDetailViewSet, basename="sale-details")
router.register(r"sale-returns", views.SaleReturnViewSet, basename="sale-returns")
router.register(r"purchases", views.PurchaseViewSet, basename="purchases")
router.register(r"products", views.ProductViewSet, basename="products")
router.register(
    r"product-variants", views.ProductVariantViewSet, basename="product-variants"
)
router.register(r"product-images", views.ProductImageViewSet, basename="product-images")
router.register(
    r"movement-inventory", views.MovementInventoryViewSet, basename="movement-inventory"
)
router.register(
    r"inventory-history", views.InventoryHistoryViewSet, basename="inventory-history"
)
router.register(
    r"inventory-report-daily", views.InventoryReportDailyViewSet, basename="inventory-report-daily"
)
# router.register(r"audit-logs", views.AuditLogViewSet, basename="audit-logs")
router.register(
    r"inventory-snapshots", views.InventorySnapshotViewSet, basename="inventory-snapshot"
)
router.register(
    r"inventory-adjustments", views.AdjustmentViewSet, basename="inventory-adjustment"
)
router.register(
    r"suppliers", views.SupplierViewSet, basename="suppliers"
)
router.register(
    r"supplier-returns", views.SupplierReturnViewSet, basename="supplier-returns"
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # JWT Authentication
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # API endpoints
    path("api/", include(router.urls)),
    path("inventory/close-month/", InventoryCloseMonthView.as_view()),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
