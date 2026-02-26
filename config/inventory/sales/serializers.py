"""
Serializers para gestión de ventas
"""
from rest_framework import serializers
from django.db import models
from django.utils import timezone
from ..models import Sale, SaleDetail, MovementInventory, ProductVariant


class EmptySerializer(serializers.Serializer):
    """Serializer vacío para acciones sin cuerpo"""
    pass


class SaleDetailCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear detalles de venta"""
    # Esto filtra las opciones que aparecen en los selectores de la API
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.filter(is_deleted=False)
    )
    sale = serializers.PrimaryKeyRelatedField(
        queryset=Sale.objects.all()
    )

    class Meta:
        model = SaleDetail
        fields = ["sale", "variant", "quantity", "price"]

    def validate_variant(self, value):
        """Validar que la variante no esté eliminada"""
        if value.is_deleted:
            raise serializers.ValidationError("Esta variante de producto ya no está disponible.")
        return value

    def create(self, validated_data):
        quantity = validated_data["quantity"]
        price = validated_data["price"]
        validated_data["subtotal"] = quantity * price
        
        # Crear el detalle
        detail = super().create(validated_data)
        
        # Actualizar el total de la venta
        sale = detail.sale
        total = sale.details.aggregate(
            total=models.Sum('subtotal')
        )['total'] or 0
        sale.total = total
        
        # Asignar created_by si no está asignado
        if not sale.created_by:
            request = self.context.get('request')
            if request and request.user:
                sale.created_by = request.user.username
        
        sale.save()
        
        return detail


class SaleCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear ventas"""
    payment_method = serializers.ChoiceField(
        choices=["CASH", "NEQUI", "DAVIPLATA", "CARD", "TRANSFER", "PSE", "OTHER"],
        required=True,
    )
    payment_reference = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=80)

    class Meta:
        model = Sale
        fields = ["customer", "is_order", "payment_method", "payment_reference"]

    def validate_payment_method(self, value: str) -> str:
        return value.strip().upper()

    def create(self, validated_data):
        # Asignar automáticamente el usuario actual como created_by
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user.username
        validated_data["payment_status"] = "paid"
        validated_data["paid_at"] = timezone.now()
        validated_data["payment_method"] = validated_data["payment_method"].strip().upper()
        validated_data["payment_reference"] = (validated_data.get("payment_reference") or "").strip() or None
        return super().create(validated_data)


class SaleSimpleSerializer(serializers.ModelSerializer):
    """Versión ligera de la venta para usar dentro de otros serializers"""
    class Meta:
        model = Sale
        fields = ["id", "customer", "status", "total", "created_at"]


class SaleDetailReadSerializer(serializers.ModelSerializer):
    """Serializer para leer detalles de venta"""
    variant = serializers.SerializerMethodField()
    sale = SaleSimpleSerializer(read_only=True)
    class Meta:
        model = SaleDetail
        fields = ["id", "sale", "variant", "quantity", "price", "subtotal"]

    def get_variant(self, obj):
        from ..products.serializers import ProductVariantSerializer
        return ProductVariantSerializer(obj.variant).data


class SaleReadSerializer(serializers.ModelSerializer):
    """Serializer para leer datos de ventas"""
    details = SaleDetailReadSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = "__all__"

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
    sale_info = SaleReadSerializer(source='sale', read_only=True)
    
    class Meta:
        model = MovementInventory
        fields = [
            'id', 'variant', 'product_name', 'product_brand', 'variant_info',
            'sale_info', 'quantity', 'observation', 'created_at', 'created_by'
        ]
        read_only_fields = ['created_at', 'created_by']
    
    def get_variant_info(self, obj):
        return f"{obj.variant.get_gender_display()} - {obj.variant.color} - {obj.variant.size}"
    
