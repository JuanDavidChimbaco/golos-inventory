"""
Serializers para gestión de ventas
"""
from rest_framework import serializers
from ..models import Sale, SaleDetail, MovementInventory


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


# Serializers para devoluciones de ventas
class SaleReturnItemSerializer(serializers.Serializer):
    """Serializer para items de devolución de venta"""
    sale_detail_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True)


class SaleReturnCreateSerializer(serializers.Serializer):
    """Serializer para crear devolución de venta"""
    sale_id = serializers.IntegerField()
    items = serializers.ListField(child=SaleReturnItemSerializer(), min_length=1)
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_sale_id(self, value):
        """Validar que la venta exista y esté completada"""
        try:
            sale = Sale.objects.get(id=value)
            if sale.status != "completed":
                raise serializers.ValidationError("Solo se pueden devolver ventas completadas")
            return value
        except Sale.DoesNotExist:
            raise serializers.ValidationError("La venta no existe")

    def validate_items(self, items):
        """Validar que los items sean válidos"""
        for item in items:
            try:
                detail = SaleDetail.objects.get(id=item['sale_detail_id'])
                if item['quantity'] > detail.quantity:
                    raise serializers.ValidationError(
                        f"No se pueden devolver más de {detail.quantity} unidades del detalle {item['sale_detail_id']}"
                    )
            except SaleDetail.DoesNotExist:
                raise serializers.ValidationError(f"El detalle de venta {item['sale_detail_id']} no existe")
        return items


class SaleReturnSerializer(serializers.ModelSerializer):
    """Serializer para mostrar devoluciones de ventas"""
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    product_brand = serializers.CharField(source='variant.product.brand', read_only=True)
    variant_info = serializers.SerializerMethodField(read_only=True)
    sale_info = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = MovementInventory
        fields = [
            'id', 'variant', 'product_name', 'product_brand', 'variant_info',
            'sale_info', 'quantity', 'observation', 'created_at', 'created_by'
        ]
        read_only_fields = ['created_at', 'created_by']
    
    def get_variant_info(self, obj):
        return f"{obj.variant.get_gender_display()} - {obj.variant.color} - {obj.variant.size}"
    
    def get_sale_info(self, obj):
        # Extraer ID de venta desde la observación
        if obj.observation and 'venta #' in obj.observation:
            try:
                sale_id = obj.observation.split('venta #')[1].split(' ')[0]
                sale = Sale.objects.get(id=sale_id)
                return {
                    'id': sale.id,
                    'customer': sale.customer,
                    'status': sale.status
                }
            except (IndexError, Sale.DoesNotExist):
                pass
        return None
