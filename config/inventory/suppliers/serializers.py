"""
Serializers para gestión de proveedores
"""
from rest_framework import serializers
from ..models import Supplier, MovementInventory


class SupplierSerializer(serializers.ModelSerializer):
    """Serializer para gestión de proveedores"""
    
    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "phone", 
            "address",
            "nit",
            "preferred_products",
            "average_price",
            "last_purchase_date",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate_average_price(self, value):
        """Validar que el precio promedio sea positivo"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("El precio promedio debe ser mayor a cero")
        return value

    def validate_name(self, value):
        """Validar que el nombre no esté duplicado"""
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre del proveedor es requerido")
        
        # Verificar duplicados (solo si es creación)
        if not self.instance:
            if Supplier.objects.filter(name__iexact=value.strip()).exists():
                raise serializers.ValidationError("Ya existe un proveedor con este nombre")
        return value.strip()


class SupplierSimpleSerializer(serializers.ModelSerializer):
    """Serializer simplificado para selects y consultas"""
    
    class Meta:
        model = Supplier
        fields = ["id", "name", "is_active", "last_purchase_date"]


# Serializers para devoluciones a proveedores
class SupplierReturnCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear devolución a proveedor"""
    
    class Meta:
        model = MovementInventory
        fields = ['variant', 'supplier', 'quantity', 'observation']
    
    def validate_quantity(self, value):
        """Validar que la cantidad sea positiva"""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a cero")
        return value
    
    def validate(self, data):
        """Validar stock disponible"""
        variant = data['variant']
        quantity = data['quantity']
        
        current_stock = variant.stock
        if current_stock < quantity:
            raise serializers.ValidationError(
                f"Stock insuficiente. Actual: {current_stock}, Requerido: {quantity}"
            )
        return data
    
    def create(self, validated_data):
        """Crear devolución a proveedor"""
        validated_data['movement_type'] = MovementInventory.MovementType.RETURN
        validated_data['quantity'] = -validated_data['quantity']  # Negativo para salida
        validated_data['created_by'] = self.context['request'].user.username
        
        if not validated_data.get('observation'):
            validated_data['observation'] = "Devolución a proveedor"
        
        return super().create(validated_data)


class SupplierReturnSerializer(serializers.ModelSerializer):
    """Serializer para mostrar devoluciones a proveedores"""
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    product_brand = serializers.CharField(source='variant.product.brand', read_only=True)
    variant_info = serializers.SerializerMethodField(read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    
    class Meta:
        model = MovementInventory
        fields = [
            'id', 'variant', 'supplier', 'supplier_name', 'product_name', 
            'product_brand', 'variant_info', 'movement_type', 'movement_type_display',
            'quantity', 'observation', 'created_at', 'created_by'
        ]
        read_only_fields = ['created_at', 'created_by']
    
    def get_variant_info(self, obj):
        return f"{obj.variant.get_gender_display()} - {obj.variant.color} - {obj.variant.size}"


class SupplierReturnBulkSerializer(serializers.Serializer):
    """Serializer para devoluciones masivas a proveedores"""
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    observation = serializers.CharField(required=False, allow_blank=True)
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    
    def validate_items(self, value):
        """Validar items de devolución masiva"""
        for item in value:
            if 'variant' not in item or 'quantity' not in item:
                raise serializers.ValidationError("Cada item debe tener 'variant' y 'quantity'")
            if item['quantity'] <= 0:
                raise serializers.ValidationError("La cantidad debe ser mayor a cero")
            
            # Validar stock disponible
            try:
                from ..models import ProductVariant
                variant = ProductVariant.objects.get(id=item['variant'])
                if variant.stock < item['quantity']:
                    raise serializers.ValidationError(
                        f"Stock insuficiente para variante {item['variant']}. "
                        f"Actual: {variant.stock}, Requerido: {item['quantity']}"
                    )
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError(f"La variante {item['variant']} no existe")
        
        return value
