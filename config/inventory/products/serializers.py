"""
Serializers para gestión de productos
"""
from rest_framework import serializers
from ..models import Product, ProductVariant, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer para imágenes de productos con validación y procesamiento
    """
    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductImage
        fields = [
            "id", "product", "variant", "image", "is_primary", "alt_text",
            "url",
            "file_size", "width", "height",
            "created_at", "updated_at", "created_by", "updated_by"
        ]
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def get_url(self, obj):
        try:
            return obj.image.url
        except Exception:
            return getattr(obj.image, "name", None)

    def validate_image(self, value):
        """Validación y procesamiento de imagen"""
        from ..core.services import ImageService
        
        try:
            # Validar imagen
            ImageService.validate_image_file(value)
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
    variants = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    def get_variants(self, obj):
        return ProductVariantSerializer(obj.variants.filter(is_deleted=False), many=True).data

    def get_image_url(self, obj):
        images = list(obj.images.all())
        if not images:
            return None

        product_primary = next(
            (img for img in images if img.variant_id is None and img.is_primary),
            None,
        )
        if product_primary:
            return ProductImageSerializer(product_primary).data["url"]

        variant_primary = next(
            (img for img in images if img.variant_id is not None and img.is_primary),
            None,
        )
        if variant_primary:
            return ProductImageSerializer(variant_primary).data["url"]

        product_first = next((img for img in images if img.variant_id is None), None)
        target = product_first or images[0]
        return ProductImageSerializer(target).data["url"]

    class Meta:
        model = Product
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    """Serializer principal para productos"""
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")
