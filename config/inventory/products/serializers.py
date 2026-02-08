"""
Serializers para gestión de productos
"""
from rest_framework import serializers
from ..models import Product, ProductVariant, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer para imágenes de productos con validación y procesamiento
    """
    class Meta:
        model = ProductImage
        fields = [
            "id", "product", "image", "is_primary", "alt_text",
            "file_size", "width", "height",
            "created_at", "updated_at", "created_by", "updated_by"
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def validate_image(self, value):
        """Validación y procesamiento de imagen"""
        from ..core.services import ImageService
        
        try:
            # Validar imagen
            ImageService.validate_image(value)
            return value
        except Exception as e:
            raise serializers.ValidationError(str(e))


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer para variantas de productos"""
    stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = "__all__"
        read_only_fields = ["created_by", "updated_by"]


class ProductReadSerializer(serializers.ModelSerializer):
    """Serializer para leer productos con relaciones"""
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    """Serializer principal para productos"""
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")
