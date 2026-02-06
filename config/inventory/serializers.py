from django.contrib.auth.models import User
from rest_framework import serializers
from .models import (
    Sale,
    SaleDetail,
    MovementInventory,
    ProductVariant,
    ProductImage,
    Product,
)


# Serializers define the API representation.


class BaseModelSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user.username
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context["request"].user.username
        return super().update(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff"]


class SaleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = ["customer", "is_order"]


class SaleDetailCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleDetail
        fields = ["sale", "variant", "quantity", "price"]

    def create(self, validated_data):
        quantity = validated_data["quantity"]
        price = validated_data["price"]

        validated_data["subtotal"] = quantity * price

        return super().create(validated_data)


class EmptySerializer(serializers.Serializer):
    pass


class MovementInventorySerializer(BaseModelSerializer):
    movement_type = serializers.ChoiceField(
        choices=[
            ("purchase", "Purchase"),
            ("adjustment", "Adjustment"),
            ("return", "Return"),
        ]
    )

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user.username
        return super().create(validated_data)

    class Meta:
        model = MovementInventory
        fields = ["variant", "movement_type", "quantity", "observation"]
        read_only_fields = ["created_by"]


class ProductVariantSerializer(BaseModelSerializer):
    class Meta:
        model = ProductVariant
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


class ProductImageSerializer(BaseModelSerializer):
    """
    Serializer para imágenes de productos con validación y procesamiento
    """
    
    def validate_image(self, value):
        """
        Valida el archivo de imagen usando el servicio
        
        Args:
            value: Archivo de imagen subido
            
        Returns:
            File: Archivo validado
            
        Raises:
            ValidationError: Si la imagen no es válida
        """
        # Usar el servicio para validar
        from .services import ImageService
        ImageService.validate_image_file(value)
        return value
    
    def create(self, validated_data):
        """
        Crea una nueva imagen de producto con procesamiento automático
        """
        # Obtener usuario del contexto
        user = self.context["request"].user
        validated_data["created_by"] = user.username
        validated_data["updated_by"] = user.username
        
        # Crear instancia sin guardar aún
        product_image = ProductImage(**validated_data)
        
        # Procesar imagen usando el servicio
        from .services import ImageService
        processed_image = ImageService.process_product_image(product_image)
        
        # Guardar la imagen procesada
        processed_image.save()
        
        return processed_image
    
    def update(self, instance, validated_data):
        """
        Actualiza una imagen existente
        """
        user = self.context["request"].user
        validated_data["updated_by"] = user.username
        
        # Si se sube una nueva imagen, procesarla
        if "image" in validated_data:
            from .services import ImageService
            instance.image = validated_data["image"]
            ImageService.process_product_image(instance)
            del validated_data["image"]  # Eliminar para evitar duplicado
        
        return super().update(instance, validated_data)
    
    class Meta:
        model = ProductImage
        fields = [
            "id", "product", "image", "is_primary", "alt_text",
            "file_size", "width", "height",
            "created_at", "updated_at", "created_by", "updated_by"
        ]
        read_only_fields = [
            "file_size", "width", "height",  # Campos autocompletados
            "created_at", "updated_at", "created_by", "updated_by"
        ]


class ProductSerializer(BaseModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "created_by", "updated_by")


# Read-only serializers for API documentation
class ProductReadSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class SaleReadSerializer(serializers.ModelSerializer):
    details = SaleDetailCreateSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = "__all__"


class SaleDetailReadSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    sale = SaleReadSerializer(read_only=True)

    class Meta:
        model = SaleDetail
        fields = "__all__"
