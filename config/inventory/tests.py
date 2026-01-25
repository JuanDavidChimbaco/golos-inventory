from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from .models import Product, ProductVariant, MovementInventory, Sale, SaleDetail
from .services import confirm_sale


class ConfirmSaleServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Crear producto
        self.product = Product.objects.create(
            name="Camiseta Test",
            brand="Nike",
            description="Camiseta de prueba",
            created_by="testuser",
        )

        # Crear variante
        self.variant = ProductVariant.objects.create(
            product=self.product,
            gender="unisex",
            color="Blanco",
            size="M",
            price=Decimal("29.99"),
            cost=Decimal("15.00"),
            stock_minimum=5,
            created_by="testuser",
        )

        # Crear venta pendiente
        self.sale = Sale.objects.create(
            customer="Cliente Test", created_by="testuser", status="pending"
        )

        # Crear detalle de venta
        self.sale_detail = SaleDetail.objects.create(
            sale=self.sale,
            variant=self.variant,
            quantity=2,
            price=Decimal("29.99"),
            subtotal=Decimal("59.98"),
        )

    def test_confirm_sale_success(self):
        """Test confirmación de venta exitosa con stock suficiente"""
        # Agregar stock inicial
        MovementInventory.objects.create(
            variant=self.variant,
            movement_type="purchase",
            quantity=10,
            created_by="testuser",
        )

        # Confirmar venta
        confirm_sale(sale_id=self.sale.id, user=self.user)

        # Verificar que la venta está completada
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, "completed")

        # Verificar que se creó el movimiento de salida
        movement = MovementInventory.objects.get(
            variant=self.variant, movement_type="sale"
        )
        self.assertEqual(movement.quantity, -2)
        self.assertEqual(movement.created_by, "testuser")

    def test_confirm_sale_insufficient_stock(self):
        """Test confirmación de venta con stock insuficiente"""
        # Agregar stock insuficiente
        MovementInventory.objects.create(
            variant=self.variant,
            movement_type="purchase",
            quantity=1,
            created_by="testuser",
        )

        # Intentar confirmar venta debe fallar
        with self.assertRaises(ValidationError) as context:
            confirm_sale(sale_id=self.sale.id, user=self.user)

        self.assertIn("Stock insuficiente", str(context.exception))

        # Verificar que la venta sigue pendiente
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, "pending")

    def test_confirm_sale_already_completed(self):
        """Test confirmación de venta ya completada"""
        self.sale.status = "completed"
        self.sale.save()

        with self.assertRaises(ValidationError) as context:
            confirm_sale(sale_id=self.sale.id, user=self.user)

        self.assertIn("no está pendiente", str(context.exception))

    def test_confirm_sale_no_details(self):
        """Test confirmación de venta sin detalles"""
        # Crear venta sin detalles
        empty_sale = Sale.objects.create(
            customer="Cliente Vacío", created_by="testuser", status="pending"
        )

        with self.assertRaises(ValidationError) as context:
            confirm_sale(sale_id=empty_sale.id, user=self.user)

        self.assertIn("no tiene Productos", str(context.exception))

    def test_confirm_sale_concurrent_transaction(self):
        """Test confirmación de venta con concurrencia"""
        # Agregar stock
        MovementInventory.objects.create(
            variant=self.variant,
            movement_type="purchase",
            quantity=5,
            created_by="testuser",
        )

        # Crear segunda venta
        sale2 = Sale.objects.create(
            customer="Cliente 2", created_by="testuser", status="pending"
        )

        SaleDetail.objects.create(
            sale=sale2,
            variant=self.variant,
            quantity=4,
            price=Decimal("29.99"),
            subtotal=Decimal("119.96"),
        )

        # Primera venta debe funcionar
        confirm_sale(sale_id=self.sale.id, user=self.user)

        # Segunda venta debe fallar por stock insuficiente
        with self.assertRaises(ValidationError):
            confirm_sale(sale_id=sale2.id, user=self.user)


class SaleDetailModelTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Producto Test", brand="Test", created_by="testuser"
        )

        self.variant = ProductVariant.objects.create(
            product=self.product,
            gender="unisex",
            color="Rojo",
            size="L",
            price=Decimal("50.00"),
            cost=Decimal("25.00"),
            created_by="testuser",
        )

        self.sale = Sale.objects.create(
            customer="Cliente Test", created_by="testuser", status="pending"
        )

    def test_sale_detail_creation(self):
        """Test creación de detalle de venta"""
        detail = SaleDetail.objects.create(
            sale=self.sale,
            variant=self.variant,
            quantity=3,
            price=Decimal("50.00"),
            subtotal=Decimal("150.00"),
        )

        self.assertEqual(detail.subtotal, Decimal("150.00"))

    def test_sale_detail_unique_constraint(self):
        """Test constraint único de sale-variant"""
        SaleDetail.objects.create(
            sale=self.sale,
            variant=self.variant,
            quantity=1,
            price=Decimal("50.00"),
            subtotal=Decimal("50.00"),
        )

        # Intentar crear duplicado debe fallar
        with self.assertRaises(Exception):  # IntegrityError
            SaleDetail.objects.create(
                sale=self.sale,
                variant=self.variant,
                quantity=2,
                price=Decimal("50.00"),
                subtotal=Decimal("100.00"),
            )


class ProductVariantModelTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Producto Test", brand="Test", created_by="testuser"
        )

    def test_product_variant_unique_together(self):
        """Test constraint único de product-gender-color-size"""
        ProductVariant.objects.create(
            product=self.product,
            gender="unisex",
            color="Azul",
            size="M",
            price=Decimal("30.00"),
            cost=Decimal("15.00"),
            created_by="testuser",
        )

        # Intentar crear duplicado debe fallar
        with self.assertRaises(Exception):  # IntegrityError
            ProductVariant.objects.create(
                product=self.product,
                gender="unisex",
                color="Azul",
                size="M",
                price=Decimal("35.00"),
                cost=Decimal("18.00"),
                created_by="testuser",
            )
