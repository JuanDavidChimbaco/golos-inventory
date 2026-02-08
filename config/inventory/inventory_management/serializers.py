"""
Serializers para gestión de inventario
"""
from rest_framework import serializers
from django.db.models import Sum
from ..models import MovementInventory, InventorySnapshot 


class MovementInventorySerializer(serializers.ModelSerializer):
    """Serializer para movimientos de inventario"""
    movement_type = serializers.ChoiceField(
        choices=[
            ("purchase", "Compra"),
            ("adjustment", "Ajuste"),
            ("return", "Devolución"),
        ]
    )
    
    class Meta:
        model = MovementInventory
        fields = ["variant", "movement_type", "quantity", "observation"]
        read_only_fields = ["created_by"]


class InventoryHistorySerializer(serializers.ModelSerializer):
    """Serializer para historial de inventario con datos adicionales"""
    product = serializers.CharField(
        source="variant.product.name",
        read_only=True
    )
    product_sku = serializers.CharField(
        source="variant.product.sku",
        read_only=True
    )
    variant_name = serializers.CharField(
        source="variant.name",
        read_only=True
    )
    variant_sku = serializers.CharField(
        source="variant.sku",
        read_only=True
    )
    movement_type_display = serializers.CharField(
        source="get_movement_type_display",
        read_only=True
    )
    stock_after = serializers.SerializerMethodField()
    stock_before = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()
    
    class Meta:
        model = MovementInventory
        fields = [
            "id", "product", "product_sku", "variant", "variant_name", 
            "variant_sku", "movement_type_display", 
            "quantity", "stock_after","stock_before","direction",
            "color", "icon", "observation", "created_at", "created_by"
        ]
        read_only_fields = ["created_at", "created_by"]

    def get_stock_after(self, obj):
        """Calcular stock acumulado - respeta arquitectura"""
        
        return MovementInventory.objects.filter(
            variant=obj.variant,
            created_at__lte=obj.created_at
        ).aggregate(total=Sum('quantity'))['total'] or 0

    def get_stock_before(self, obj):
        return self.get_stock_after(obj) - obj.quantity

    def get_movement_type_display(self, obj):
        mapping = {
            "purchase": "Compra",
            "adjustment": "Ajuste",
            "return": "Devolución",
            "sale_out": "Venta",
            "sale_return": "Devolución de venta",
        }
        return mapping.get(obj.movement_type, obj.movement_type)

    def get_direction(self, obj):
        """
        Determina si el movimiento es entrada, salida o neutro
        """
        if obj.movement_type in ["purchase", "sale_return", "return"]:
            return "in"
        if obj.movement_type == "sale_out":
            return "out"
        return "adjustment"
    
    def get_color(self, obj):
        """
        Color sugerido para UI según el tipo de movimiento
        """
        if obj.movement_type in ["purchase", "sale_return", "return"]:
            return "green"
        if obj.movement_type == "sale_out":
            return "red"

        # adjustment
        if obj.quantity > 0:
            return "green"
        if obj.quantity < 0:
            return "red"

        return "gray"

    def get_icon(self, obj):
        if obj.movement_type in ["purchase", "sale_return", "return"]:
            return "⬆️"
        if obj.movement_type in ["sale_out","sale"]:
            return "⬇️"
        return "🔧"


class DailyInventorySummarySerializer(serializers.Serializer):
    day = serializers.DateField()
    total_in = serializers.IntegerField() 
    total_out = serializers.IntegerField()
    balance = serializers.IntegerField(read_only=True)


class InventorySnapshotSerializer(serializers.ModelSerializer): 
    product = serializers.CharField(
        source="variant.product.name",
        read_only=True
    )
    product_sku = serializers.CharField(
        source="variant.product.sku",
        read_only=True
    )
    variant_color = serializers.CharField(
        source="variant.color",
        read_only=True
    )
    variant_size = serializers.CharField(
        source="variant.size",
        read_only=True
    )

    class Meta:
        model = InventorySnapshot
        fields = [
            "id",
            "month",
            "product",
            "product_sku",
            "variant",
            "variant_color",
            "variant_size",
            "stock_opening",
            "total_in",
            "total_out",
            "stock_closing",
            "created_at",
        ]
        read_only_fields = fields