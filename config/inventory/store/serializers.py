"""
Serializers para API publica de tienda.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from ..models import ProductImage, ProductVariant, Shipment, StoreBranding


class StoreVariantSerializer(serializers.ModelSerializer):
    stock = serializers.IntegerField(source="current_stock", read_only=True)

    class Meta:
        model = ProductVariant
        fields = ["id", "gender", "color", "size", "price", "stock", "stock_minimum"]


class StoreProductSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    brand = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    product_type = serializers.CharField(read_only=True)
    image_url = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        best_image = self._select_primary_image(obj)
        if not best_image:
            return None

        return self._resolve_image_url(best_image.image)

    def get_images(self, obj):
        images = self._filter_store_images(obj)
        return [
            {
                "id": image.id,
                "url": self._resolve_image_url(image.image),
                "is_primary": image.is_primary,
                "alt_text": image.alt_text,
                "variant_id": image.variant_id,
            }
            for image in images
        ]

    def _resolve_image_url(self, image_field) -> str | None:
        try:
            return image_field.url
        except Exception:
            return getattr(image_field, "name", None)

    def _filter_store_images(self, obj) -> list[ProductImage]:
        images = list(getattr(obj, "store_images", []))
        if not images:
            return []

        available_variant_ids = {
            variant.id for variant in getattr(obj, "store_variants", []) if getattr(variant, "id", None)
        }

        return [
            image
            for image in images
            if image.variant_id is None or image.variant_id in available_variant_ids
        ]

    def _select_primary_image(self, obj) -> ProductImage | None:
        images = self._filter_store_images(obj)
        if not images:
            return None

        product_primary = next(
            (image for image in images if image.variant_id is None and image.is_primary),
            None,
        )
        if product_primary:
            return product_primary

        variant_primary = next(
            (image for image in images if image.variant_id is not None and image.is_primary),
            None,
        )
        if variant_primary:
            return variant_primary

        product_first = next((image for image in images if image.variant_id is None), None)
        return product_first or images[0]

    def get_variants(self, obj):
        variants = getattr(obj, "store_variants", [])
        return StoreVariantSerializer(variants, many=True).data


class StoreItemsValidationSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.DictField(), min_length=1)

    def validate_items(self, items: list[dict]) -> list[dict]:
        # Consolidar cantidades repetidas por variante para validacion y total coherente.
        quantities_by_variant: dict[int, int] = {}
        for item in items:
            item_serializer = StoreCartItemSerializer(data=item)
            item_serializer.is_valid(raise_exception=True)
            variant_id = item_serializer.validated_data["variant_id"]
            quantities_by_variant[variant_id] = quantities_by_variant.get(variant_id, 0) + item_serializer.validated_data["quantity"]

        variants = ProductVariant.objects.filter(
            id__in=quantities_by_variant.keys(),
            is_deleted=False,
            active=True,
        ).select_related("product")
        variant_map = {variant.id: variant for variant in variants}

        errors: list[str] = []
        normalized_items: list[dict] = []
        for variant_id, requested_qty in quantities_by_variant.items():
            variant = variant_map.get(variant_id)
            if not variant:
                errors.append(f"Variante #{variant_id} no disponible")
                continue

            available = int(variant.stock)
            if requested_qty > available:
                errors.append(
                    f"Stock insuficiente para {variant.product.name}. Disponible: {available}, Requerido: {requested_qty}"
                )
                continue

            normalized_items.append(
                {
                    "variant": variant,
                    "quantity": requested_qty,
                    "unit_price": Decimal(variant.price),
                    "subtotal": Decimal(variant.price) * requested_qty,
                    "available_stock": available,
                }
            )

        if errors:
            raise serializers.ValidationError(errors)

        return normalized_items


class StoreCartItemSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)

    def validate_variant_id(self, value: int) -> int:
        if not ProductVariant.objects.filter(id=value, is_deleted=False, active=True).exists():
            raise serializers.ValidationError("La variante seleccionada no existe o no esta disponible.")
        return value


class StoreCartValidateSerializer(serializers.Serializer):
    items = serializers.ListField(child=StoreCartItemSerializer(), min_length=1)
    shipping_zone = serializers.ChoiceField(
        choices=["local", "regional", "national"],
        required=False,
        default="regional",
    )
    estimated_weight_grams = serializers.IntegerField(required=False, min_value=1)

    def validate_items(self, items: list[dict]) -> list[dict]:
        validator = StoreItemsValidationSerializer(data={"items": items})
        validator.is_valid(raise_exception=True)
        return validator.validated_data["items"]


class StoreCheckoutSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=100)
    customer_contact = serializers.CharField(max_length=100, required=False, allow_blank=True)
    items = serializers.ListField(child=StoreCartItemSerializer(), min_length=1)
    is_order = serializers.BooleanField(required=False, default=True)
    shipping_zone = serializers.ChoiceField(
        choices=["local", "regional", "national"],
        required=False,
        default="regional",
    )
    estimated_weight_grams = serializers.IntegerField(required=False, min_value=1)
    shipping_address = serializers.DictField(required=True)

    def validate_shipping_address(self, value: dict) -> dict:
        required_keys = ["department", "city", "address_line1", "recipient_name", "recipient_phone"]
        cleaned: dict[str, str] = {}
        for key in required_keys:
            field_value = str(value.get(key, "")).strip()
            if not field_value:
                raise serializers.ValidationError(f"{key} es requerido.")
            cleaned[key] = field_value

        optional_keys = ["address_line2", "reference", "postal_code"]
        for key in optional_keys:
            cleaned[key] = str(value.get(key, "")).strip()

        return cleaned

    def validate_items(self, items: list[dict]) -> list[dict]:
        validator = StoreItemsValidationSerializer(data={"items": items})
        validator.is_valid(raise_exception=True)
        return validator.validated_data["items"]


class StoreBrandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreBranding
        fields = [
            "store_name",
            "tagline",
            "logo_url",
            "hero_title",
            "hero_subtitle",
            "updated_at",
        ]


class StoreBrandingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreBranding
        fields = [
            "store_name",
            "tagline",
            "logo_url",
            "hero_title",
            "hero_subtitle",
        ]


class StoreCustomerRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("El username ya existe.")
        return value

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("El email ya esta registrado.")
        return value


class StoreCustomerLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Credenciales invalidas.")
        if not user.is_active:
            raise serializers.ValidationError("La cuenta esta inactiva.")
        attrs["user"] = user
        return attrs


class StoreOpsManualShipmentSerializer(serializers.Serializer):
    carrier = serializers.CharField(max_length=60)
    tracking_number = serializers.CharField(max_length=80)
    shipping_cost = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))
    service = serializers.CharField(max_length=60, required=False, allow_blank=True, default="manual")
    provider_reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    label_url = serializers.URLField(required=False, allow_blank=True)
    currency = serializers.CharField(max_length=10, required=False, allow_blank=True, default="COP")
    status = serializers.ChoiceField(
        choices=Shipment.ShipmentStatus.choices,
        required=False,
        default=Shipment.ShipmentStatus.IN_TRANSIT,
    )

    def validate_tracking_number(self, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise serializers.ValidationError("tracking_number es requerido.")
        return normalized

    def validate_carrier(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError("carrier es requerido.")
        return normalized
