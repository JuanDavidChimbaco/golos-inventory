"""
Serializers para gestión de proveedores
"""
from rest_framework import serializers
from ..models import Supplier


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
