"""
Views para gestión de productos
"""
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db.models import F, Exists, OuterRef
from ..models import Product, ProductVariant, ProductImage
from ..core.services import ImageService
from .serializers import (
    ProductSerializer,
    ProductReadSerializer,
    ProductVariantSerializer,
    ProductImageSerializer,
)

@extend_schema(tags=['Products'])
class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de productos
    
    - Lectura: Usuarios autenticados
    - Creación: Usuarios con permiso add_product
    - Actualización: Usuarios con permiso change_product
    - Eliminación: Usuarios con permiso delete_product
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    filterset_fields = ['brand', 'active', 'product_type']
    search_fields = ['name', 'brand', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ProductReadSerializer
        return ProductSerializer


@extend_schema(tags=['ProductsVariants'])
class ProductVariantViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de variantas de productos
    
    - Requiere permisos de inventario
    """
    queryset = ProductVariant.objects.all().select_related('product')
    serializer_class = ProductVariantSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    filterset_fields = ['product', 'gender', 'color', 'active']
    search_fields = ['product__name', 'product__brand', 'color', 'size']
    ordering_fields = ['price', 'cost', 'created_at', 'product__name']
    ordering = ['product__name', 'color', 'size']
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema(tags=['ProductsImages'])
class ProductImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de imágenes de productos
    
    - Requiere permisos de inventario
    """
    queryset = ProductImage.objects.all().select_related('product')
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def perform_create(self, serializer):
        """Extrae metadatos de imagen, optimiza y registra usuario"""
        try:
            image_file = serializer.validated_data['image']
            metadata = ImageService.extract_image_metadata(image_file)
            
            # Optimizar imagen (redimensionar y comprimir)
            ImageService.optimize_image(image_file)
            
            # Extraer metadatos nuevamente después de la optimización
            metadata = ImageService.extract_image_metadata(image_file)
            
            serializer.save(
                file_size=metadata['file_size'],
                width=metadata['width'],
                height=metadata['height'],
                created_by=self.request.user.username,
                updated_by=self.request.user.username
            )
        except Exception as e:
            raise DRFValidationError(f"Error procesando imagen: {str(e)}")

    def perform_update(self, serializer):
        """Actualiza metadatos de usuario"""
        serializer.save(updated_by=self.request.user.username)
