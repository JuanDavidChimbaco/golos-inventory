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
    
    - Lectura: Usuarios autenticados con permiso view_product
    - Escritura: Usuarios autenticados con permiso add/change/delete_product
    """
    queryset = Product.objects.all().prefetch_related('variants', 'images')
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

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
