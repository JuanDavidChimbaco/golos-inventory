"""
Views para gestión de productos
"""
from rest_framework import viewsets, permissions
from rest_framework.exceptions import ValidationError as DRFValidationError
from ..models import Product, ProductVariant, ProductImage
from .serializers import (
    ProductSerializer,
    ProductReadSerializer,
    ProductVariantSerializer,
    ProductImageSerializer,
)


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
    filterset_fields = ['brand', 'active']
    search_fields = ['name', 'brand', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ProductReadSerializer
        return ProductSerializer


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


class ProductImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de imágenes de productos
    
    - Requiere permisos de inventario
    """
    queryset = ProductImage.objects.all().select_related('product')
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def perform_create(self, serializer):
        """Extrae metadatos de imagen y registra usuario"""
        try:
            image_file = serializer.validated_data['image']
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
