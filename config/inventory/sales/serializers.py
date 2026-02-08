"""
Serializers para gestión de ventas
"""
from rest_framework import serializers
from ..models import Sale, SaleDetail


class EmptySerializer(serializers.Serializer):
    """Serializer vacío para acciones sin cuerpo"""
    pass


class SaleDetailCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear detalles de venta"""
    class Meta:
        model = SaleDetail
        fields = ["sale", "variant", "quantity", "price"]

    def create(self, validated_data):
        quantity = validated_data["quantity"]
        price = validated_data["price"]
        validated_data["subtotal"] = quantity * price
        return super().create(validated_data)


class SaleCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear ventas"""
    class Meta:
        model = Sale
        fields = ["customer", "is_order"]


class SaleReadSerializer(serializers.ModelSerializer):
    """Serializer para leer datos de ventas"""
    details = SaleDetailCreateSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = "__all__"


class SaleDetailReadSerializer(serializers.ModelSerializer):
    """Serializer para leer detalles de venta"""
    variant = serializers.SerializerMethodField()
    sale = SaleReadSerializer(read_only=True)

    class Meta:
        model = SaleDetail
        fields = "__all__"

    def get_variant(self, obj):
        from ..products.serializers import ProductVariantSerializer
        return ProductVariantSerializer(obj.variant).data
