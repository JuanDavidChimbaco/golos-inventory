"""
    Serializers para la gestión de compras
"""
from rest_framework import serializers
from ..models import MovementInventory, Supplier, ProductVariant, Product


class VariantNestedSerializer(serializers.ModelSerializer):
    """Serializer anidado para variante"""
    product = serializers.SerializerMethodField(read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    size_display = serializers.CharField(source='size', read_only=True)  # Para consistencia

    class Meta:
        model = ProductVariant
        fields = ['id', 'product', 'size', 'color', 'gender', 'gender_display', 'size_display', 'cost', 'active']

    def get_product(self, obj):
        return {
            'id': obj.product.id,
            'name': obj.product.name,
            'brand': obj.product.brand
        }


class SupplierNestedSerializer(serializers.ModelSerializer):
    """Serializer anidado para proveedor"""

    class Meta:
        model = Supplier
        fields = ['id', 'name', 'nit', 'phone', 'address', 'is_active']


class PurchaseDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalles de compra individual"""
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    product_brand = serializers.CharField(source='variant.product.brand', read_only=True)
    variant_info = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = MovementInventory
        fields = [
            'id', 'variant', 'product_name', 'product_brand', 'variant_info',
            'quantity', 'observation', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_variant_info(self, obj):
        return f"{obj.variant.get_gender_display()} - {obj.variant.color} - {obj.variant.size}"


class PurchaseSerializer(serializers.ModelSerializer):
    """Serializer principal para compras"""
    variant = VariantNestedSerializer(read_only=True)
    supplier = SupplierNestedSerializer(read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    unit_cost = serializers.SerializerMethodField(read_only=True)
    total_cost = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = MovementInventory
        fields = [
            'id', 'variant', 'supplier', 'movement_type',
            'movement_type_display', 'quantity', 'unit_cost', 'total_cost', 'observation', 'created_at', 'created_by'
        ]
        read_only_fields = ['created_at', 'created_by', 'movement_type']
    
    def get_unit_cost(self, obj):
        return obj.variant.cost
    
    def get_total_cost(self, obj):
        return obj.quantity * obj.variant.cost
    
    def create(self, validated_data):
        """Crear una compra automáticamente estableciendo el tipo de movimiento"""
        validated_data['movement_type'] = MovementInventory.MovementType.PURCHASE
        validated_data['created_by'] = self.context['request'].user.username
        return super().create(validated_data)


class PurchaseCreateSerializer(serializers.ModelSerializer):
    """Serializer simplificado para crear compras"""
    
    class Meta:
        model = MovementInventory
        fields = ['variant', 'supplier', 'quantity', 'observation']
    
    def validate_quantity(self, value):
        """Validar que la cantidad sea positiva para compras"""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a cero para compras.")
        return value
    
    def create(self, validated_data):
        """Crear una compra automáticamente estableciendo el tipo de movimiento y usuario"""
        validated_data['movement_type'] = MovementInventory.MovementType.PURCHASE
        validated_data['created_by'] = self.context['request'].user.username
        return super().create(validated_data)


class BulkPurchaseSerializer(serializers.Serializer):
    """Serializer para compras masivas"""
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    observation = serializers.CharField(required=False, allow_blank=True)
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    
    def validate_items(self, value):
        """Validar que cada item tenga los campos necesarios"""
        for item in value:
            if 'variant' not in item or 'quantity' not in item:
                raise serializers.ValidationError("Cada item debe tener 'variant' y 'quantity'")
            if item['quantity'] <= 0:
                raise serializers.ValidationError("La cantidad debe ser mayor a cero")
        return value
    
    def create(self, validated_data):
        """Crear múltiples movimientos de compra"""
        supplier = validated_data['supplier']
        observation = validated_data.get('observation', '')
        items = validated_data['items']
        created_by = self.context['request'].user.username
        
        movements = []
        for item in items:
            movement = MovementInventory.objects.create(
                variant_id=item['variant'],
                supplier=supplier,
                quantity=item['quantity'],
                observation=observation,
                movement_type=MovementInventory.MovementType.PURCHASE,
                created_by=created_by
            )
            movements.append(movement)
        
        return movements

