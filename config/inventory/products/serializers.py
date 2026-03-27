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
        """
        Obtener la URL de la imagen almacenada.
        
        Args:
            obj: Instancia de ProductImage
            
        Returns:
            str or None: URL de la imagen o None si no se puede obtener
        """
        try:
            return obj.image.url
        except Exception:
            return getattr(obj.image, "name", None)

    def validate_image(self, value):
        """
        Validar y procesar la imagen usando el servicio de imágenes.
        
        Args:
            value: Archivo de imagen a validar
            
        Returns:
            file: Archivo de imagen validado
            
        Raises:
            ValidationError: Si la imagen no es válida
        """
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
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_brand = serializers.CharField(source='product.brand', read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product', 'product_name', 'product_brand', 'image_url',
            'gender', 'color', 'size', 
            'price', 'cost', 'stock_minimum', 'stock', 'active', 
            'created_at', 'updated_at', 'is_deleted'
        ]
        read_only_fields = ["created_by", "updated_by"]

    def get_image_url(self, obj):
        """Obtener URL de imagen principal del producto padre."""
        try:
            img = obj.product.images.filter(is_primary=True, variant__isnull=True).first()
            if not img:
                img = obj.product.images.first()
            if img and img.image:
                return img.image.url
        except Exception:
            pass
        return None


class ProductReadSerializer(serializers.ModelSerializer):
    """Serializer para leer productos con relaciones"""
    images = ProductImageSerializer(many=True, read_only=True)
    variants = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    def get_variants(self, obj):
        """
        Obtener las variantes del producto que no están eliminadas.
        
        Args:
            obj: Instancia de Product
            
        Returns:
            list: Lista de variantes serializadas
        """
        return ProductVariantSerializer(obj.variants.filter(is_deleted=False), many=True).data

    def get_image_url(self, obj):
        """
        Obtener la URL de la imagen principal del producto.
        
        Prioridad: imagen primaria del producto > imagen primaria de variante > primera imagen del producto > primera imagen.
        
        Args:
            obj: Instancia de Product
            
        Returns:
            str or None: URL de la imagen principal o None si no hay imágenes
        """
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
