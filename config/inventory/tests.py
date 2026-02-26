from django.test import TestCase, override_settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json
from PIL import Image
from io import BytesIO
from unittest.mock import patch
from .models import Product, ProductVariant, MovementInventory, Sale, SaleDetail, ProductImage, Shipment, ShipmentEvent, Supplier
from .core.services import confirm_sale, ImageService
from .store.shipping import shipping_webhook_signature


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


class ImageServiceTest(TestCase):
    """Tests para el servicio de imágenes"""
    
    def setUp(self):
        self.product = Product.objects.create(
            name="Producto Test", brand="Test", created_by="testuser"
        )
    
    def create_test_image(self, size=(100, 100), format='JPEG', name='test.jpg'):
        """Crea una imagen de prueba"""
        img = Image.new('RGB', size, color='red')
        img_io = BytesIO()
        img.save(img_io, format=format)
        img_io.seek(0)
        return SimpleUploadedFile(name, img_io.getvalue(), content_type=f'image/{format.lower()}')
    
    def test_validate_image_file_success(self):
        """Test validación exitosa de imagen válida"""
        image = self.create_test_image()
        
        # No debe lanzar excepción
        try:
            ImageService.validate_image_file(image)
        except ValidationError:
            self.fail("validate_image_file() lanzó ValidationError inesperadamente")
    
    def test_validate_image_file_too_large(self):
        """Test validación falla por tamaño excesivo"""
        # Crear imagen grande (simulando 3MB)
        large_image = SimpleUploadedFile(
            "large.jpg", 
            b'x' * (3 * 1024 * 1024),  # 3MB
            content_type="image/jpeg"
        )
        
        with self.assertRaises(ValidationError) as context:
            ImageService.validate_image_file(large_image)
        
        self.assertIn("demasiado grande", str(context.exception))
    
    def test_validate_image_file_invalid_format(self):
        """Test validación falla por formato inválido"""
        # Crear archivo que no es imagen
        invalid_file = SimpleUploadedFile(
            "test.txt", 
            b"esto no es una imagen",
            content_type="text/plain"
        )
        
        with self.assertRaises(ValidationError) as context:
            ImageService.validate_image_file(invalid_file)
        
        self.assertIn("no es una imagen válida", str(context.exception))
    
    def test_extract_image_metadata_success(self):
        """Test extracción correcta de metadatos"""
        image = self.create_test_image(size=(200, 150))
        metadata = ImageService.extract_image_metadata(image)
        
        self.assertEqual(metadata['width'], 200)
        self.assertEqual(metadata['height'], 150)
        self.assertEqual(metadata['format'], 'JPEG')
        self.assertGreater(metadata['file_size'], 0)
    
    def test_extract_image_metadata_invalid_file(self):
        """Test extracción con archivo inválido"""
        invalid_file = SimpleUploadedFile(
            "invalid.txt", 
            b"no es imagen",
            content_type="text/plain"
        )
        metadata = ImageService.extract_image_metadata(invalid_file)
        
        self.assertEqual(metadata['width'], 0)
        self.assertEqual(metadata['height'], 0)
        self.assertEqual(metadata['format'], 'Unknown')
        self.assertGreater(metadata['file_size'], 0)
    
    def test_process_product_image_success(self):
        """Test procesamiento completo de imagen"""
        image = self.create_test_image(size=(300, 200))
        
        # Crear instancia sin guardar
        product_image = ProductImage(
            product=self.product,
            image=image,
            is_primary=True,
            alt_text="Imagen de prueba"
        )
        
        # Procesar
        processed = ImageService.process_product_image(product_image)
        
        # Verificar metadatos
        self.assertEqual(processed.width, 300)
        self.assertEqual(processed.height, 200)
        self.assertGreater(processed.file_size, 0)
        self.assertEqual(processed.product, self.product)
        self.assertTrue(processed.is_primary)
        self.assertEqual(processed.alt_text, "Imagen de prueba")
    
    def test_set_primary_image(self):
        """Test establecer imagen principal"""
        # Crear múltiples imágenes
        image1 = self.create_test_image()
        image2 = self.create_test_image()
        
        product_image1 = ProductImage.objects.create(
            product=self.product,
            image=image1,
            is_primary=False,
            created_by="testuser"
        )
        product_image2 = ProductImage.objects.create(
            product=self.product,
            image=image2,
            is_primary=False,
            created_by="testuser"
        )
        
        # Establecer segunda como principal
        ImageService.set_primary_image(self.product, product_image2.id)
        
        # Verificar que solo la segunda es principal
        product_image1.refresh_from_db()
        product_image2.refresh_from_db()
        
        self.assertFalse(product_image1.is_primary)
        self.assertTrue(product_image2.is_primary)


class ProductImageSerializerTest(TestCase):
    """Tests para el serializer de imágenes"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.product = Product.objects.create(
            name="Producto Test", brand="Test", created_by="testuser"
        )
    
    def create_test_image(self, size=(100, 100), format='JPEG', name='test.jpg'):
        """Crea una imagen de prueba"""
        img = Image.new('RGB', size, color='blue')
        img_io = BytesIO()
        img.save(img_io, format=format)
        img_io.seek(0)
        return SimpleUploadedFile(name, img_io.getvalue(), content_type=f'image/{format.lower()}')
    
    def test_serializer_create_success(self):
        """Test creación exitosa vía serializer"""
        from .serializers import ProductImageSerializer
        
        image = self.create_test_image()
        data = {
            'product': self.product.id,
            'image': image,
            'is_primary': True,
            'alt_text': 'Imagen principal'
        }
        
        serializer = ProductImageSerializer(
            data=data,
            context={'request': type('Request', (), {'user': self.user})()}
        )
        
        self.assertTrue(serializer.is_valid())
        product_image = serializer.save()
        
        # Verificar que se guardó correctamente
        self.assertEqual(product_image.product, self.product)
        self.assertTrue(product_image.is_primary)
        self.assertEqual(product_image.alt_text, 'Imagen principal')
        self.assertEqual(product_image.created_by, 'testuser')
        
        # Verificar metadatos autocompletados
        self.assertIsNotNone(product_image.width)
        self.assertIsNotNone(product_image.height)
        self.assertIsNotNone(product_image.file_size)
    
    def test_serializer_validate_image_too_large(self):
        """Test validación de imagen muy grande"""
        from .serializers import ProductImageSerializer
        
        # Crear imagen grande pero válida para DRF
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        
        # Modificar el tamaño del archivo para simular 3MB
        large_content = img_io.getvalue() + (b'x' * (3 * 1024 * 1024 - len(img_io.getvalue())))
        large_image = SimpleUploadedFile(
            "large.jpg", 
            large_content,
            content_type="image/jpeg"
        )
        
        data = {
            'product': self.product.id,
            'image': large_image,
            'is_primary': False,
            'alt_text': ''
        }
        
        serializer = ProductImageSerializer(
            data=data,
            context={'request': type('Request', (), {'user': self.user})()}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('image', serializer.errors)
        # Puede ser nuestro mensaje o el de DRF
        error_message = str(serializer.errors['image'])
        self.assertTrue(
            'demasiado grande' in error_message or 'invalid' in error_message
        )
    
    def test_serializer_update_with_new_image(self):
        """Test actualización con nueva imagen"""
        from .serializers import ProductImageSerializer
        
        # Crear imagen inicial
        initial_image = self.create_test_image(size=(100, 100))
        product_image = ProductImage.objects.create(
            product=self.product,
            image=initial_image,
            is_primary=False,
            created_by="testuser"
        )
        
        # Crear nueva imagen
        new_image = self.create_test_image(size=(200, 200))
        data = {
            'image': new_image,
            'alt_text': 'Imagen actualizada'
        }
        
        serializer = ProductImageSerializer(
            instance=product_image,
            data=data,
            partial=True,
            context={'request': type('Request', (), {'user': self.user})()}
        )
        
        self.assertTrue(serializer.is_valid())
        updated_image = serializer.save()
        
        # Verificar actualización
        self.assertEqual(updated_image.alt_text, 'Imagen actualizada')
        self.assertEqual(updated_image.updated_by, 'testuser')
        
        # Verificar que los metadatos se actualizaron
        self.assertEqual(updated_image.width, 200)
        self.assertEqual(updated_image.height, 200)
    
    def test_serializer_read_only_fields(self):
        """Test que los campos autocompletados son read-only"""
        from .serializers import ProductImageSerializer
        
        image = self.create_test_image()
        data = {
            'product': self.product.id,
            'image': image,
            'file_size': 999999,  # Intento de manipulación
            'width': 5000,        # Intento de manipulación
            'height': 5000,       # Intento de manipulación
        }
        
        serializer = ProductImageSerializer(
            data=data,
            context={'request': type('Request', (), {'user': self.user})()}
        )
        
        self.assertTrue(serializer.is_valid())
        product_image = serializer.save()
        
        # Verificar que los campos no fueron manipulados
        self.assertNotEqual(product_image.file_size, 999999)
        self.assertNotEqual(product_image.width, 5000)
        self.assertNotEqual(product_image.height, 5000)


class ApiErrorContractTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="apiadmin",
            email="apiadmin@example.com",
            password="adminpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.product = Product.objects.create(
            name="Air Contract Test",
            brand="Nike",
            description="Producto para test de contrato",
            created_by=self.user.username,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            gender="unisex",
            color="Negro",
            size="42",
            price=Decimal("120.00"),
            cost=Decimal("80.00"),
            stock_minimum=2,
            created_by=self.user.username,
        )
        self.sale = Sale.objects.create(
            customer="Cliente API Test",
            created_by=self.user.username,
            status="pending",
        )
        SaleDetail.objects.create(
            sale=self.sale,
            variant=self.variant,
            quantity=3,
            price=Decimal("120.00"),
            subtotal=Decimal("360.00"),
        )
        MovementInventory.objects.create(
            variant=self.variant,
            movement_type=MovementInventory.MovementType.PURCHASE,
            quantity=1,
            created_by=self.user.username,
        )

    def test_confirm_sale_insufficient_stock_returns_standard_error_contract(self):
        url = reverse("sales-confirm", args=[self.sale.id])
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 409)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertIn("errors", response.data)
        self.assertEqual(response.data["code"], "SALE_CONFIRMATION_FAILED")
        self.assertIsInstance(response.data["errors"], list)
        self.assertTrue(any("Stock insuficiente" in message for message in response.data["errors"]))

    def test_purchase_supplier_purchases_missing_supplier_id_returns_standard_error_contract(self):
        url = reverse("purchases-supplier-purchases")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertIn("errors", response.data)
        self.assertEqual(response.data["code"], "MISSING_SUPPLIER_ID")
        self.assertIsInstance(response.data["errors"], list)

    def test_batch_update_prices_missing_updates_returns_standard_error_contract(self):
        url = reverse("batch-update-prices")
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertIn("errors", response.data)
        self.assertEqual(response.data["code"], "MISSING_UPDATES")
        self.assertIsInstance(response.data["errors"], list)

    def test_supplier_purchase_missing_items_returns_standard_error_contract(self):
        supplier = Supplier.objects.create(
            name="Proveedor Test",
            nit="900123456-7",
            phone="3000000000",
            created_by=self.user.username,
        )
        url = reverse("suppliers-purchase", args=[supplier.id])
        response = self.client.post(url, {"items": []}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertIn("errors", response.data)
        self.assertEqual(response.data["code"], "MISSING_ITEMS")
        self.assertIsInstance(response.data["errors"], list)

    def test_inventory_close_month_missing_month_returns_standard_error_contract(self):
        response = self.client.post("/inventory/close-month/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertIn("errors", response.data)
        self.assertEqual(response.data["code"], "MISSING_MONTH")
        self.assertIsInstance(response.data["errors"], list)

    def test_inventory_close_month_invalid_month_format_returns_standard_error_contract(self):
        response = self.client.post("/inventory/close-month/", {"month": "2026/13"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertIn("errors", response.data)
        self.assertEqual(response.data["code"], "INVALID_MONTH_FORMAT")
        self.assertIsInstance(response.data["errors"], list)

    def test_confirm_sale_not_found_returns_standard_error_contract(self):
        url = reverse("sales-confirm", args=[999999])
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertIn("errors", response.data)
        self.assertEqual(response.data["code"], "SALE_NOT_FOUND")
        self.assertIsInstance(response.data["errors"], list)

    def test_confirm_sale_success_returns_standard_success_contract(self):
        MovementInventory.objects.create(
            variant=self.variant,
            movement_type=MovementInventory.MovementType.PURCHASE,
            quantity=5,
            created_by=self.user.username,
        )
        url = reverse("sales-confirm", args=[self.sale.id])
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertEqual(response.data["code"], "SALE_CONFIRMED")
        self.assertIn("Venta confirmada", response.data["detail"])

    def test_batch_update_prices_success_returns_standard_success_contract(self):
        url = reverse("batch-update-prices")
        payload = {
            "updates": [
                {
                    "variant_id": self.variant.id,
                    "price": 130,
                    "cost": 90,
                }
            ]
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertEqual(response.data["code"], "BATCH_PRICES_UPDATED")
        self.assertIn("updated_count", response.data)

    def test_inventory_close_month_success_returns_standard_success_contract(self):
        past_month = (timezone.now().date().replace(day=1) - timedelta(days=1)).replace(day=1)
        response = self.client.post(
            "/inventory/close-month/",
            {"month": past_month.strftime("%Y-%m-%d")},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertEqual(response.data["code"], "MONTH_CLOSED")

    def test_dashboard_overview_success_returns_standard_success_contract(self):
        url = reverse("dashboard-overview")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertEqual(response.data["code"], "DASHBOARD_OVERVIEW_OK")
        self.assertIn("products", response.data)

    def test_notifications_low_stock_alerts_success_returns_standard_success_contract(self):
        url = reverse("notifications-low-stock-alerts")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertEqual(response.data["code"], "NOTIFICATIONS_LOW_STOCK_ALERTS_OK")
        self.assertIn("summary", response.data)

    def test_notifications_supplier_recommendations_success_returns_standard_success_contract(self):
        supplier = Supplier.objects.create(
            name="Proveedor Recomendado",
            nit="900765432-1",
            phone="3001112233",
            created_by=self.user.username,
            is_active=True,
        )
        supplier.preferred_products.add(self.product)

        url = reverse("notifications-supplier-recommendations")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertEqual(response.data["code"], "NOTIFICATIONS_SUPPLIER_RECOMMENDATIONS_OK")
        self.assertIn("recommendations", response.data)

    def test_products_detail_includes_image_url_and_images_url(self):
        ProductImage.objects.create(
            product=self.product,
            variant=self.variant,
            image="products/contract-test.jpg",
            is_primary=True,
            alt_text="Imagen contrato",
            created_by=self.user.username,
            updated_by=self.user.username,
        )

        url = reverse("products-detail", args=[self.product.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("image_url", response.data)
        self.assertIsNotNone(response.data["image_url"])
        self.assertIn("images", response.data)
        self.assertGreaterEqual(len(response.data["images"]), 1)
        self.assertIn("url", response.data["images"][0])
        self.assertIsNotNone(response.data["images"][0]["url"])


@override_settings(STORE_MARGIN_GUARD_ENABLED=False)
class StorePublicApiTest(APITestCase):
    def setUp(self):
        self.ops_user = User.objects.create_superuser(
            username="storeops",
            email="storeops@example.com",
            password="storeops123",
        )
        customers_group, _ = Group.objects.get_or_create(name="Customers")
        self.customer_user = User.objects.create_user(
            username="cliente_store_tests",
            email="cliente_store_tests@example.com",
            password="secret1234",
            first_name="Cliente",
            last_name="Tests",
            is_staff=False,
        )
        self.customer_user.groups.add(customers_group)
        self.product = Product.objects.create(
            name="Tenis Publicos",
            brand="Golos",
            description="Modelo para tienda online",
            created_by="system",
            updated_by="system",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            gender="unisex",
            color="Negro",
            size="40",
            price=Decimal("199.90"),
            cost=Decimal("120.00"),
            stock_minimum=2,
            created_by="system",
            updated_by="system",
            active=True,
        )
        MovementInventory.objects.create(
            variant=self.variant,
            movement_type=MovementInventory.MovementType.PURCHASE,
            quantity=8,
            created_by="system",
        )
        ProductImage.objects.create(
            product=self.product,
            variant=self.variant,
            image="products/store-variant.jpg",
            is_primary=True,
            alt_text="Imagen variante principal",
            created_by="system",
            updated_by="system",
        )
        self.product_b = Product.objects.create(
            name="Botas Urbanas",
            brand="Golos",
            description="Segundo producto para filtros",
            product_type="boots",
            created_by="system",
            updated_by="system",
        )
        self.variant_b = ProductVariant.objects.create(
            product=self.product_b,
            gender="female",
            color="Cafe",
            size="38",
            price=Decimal("249.90"),
            cost=Decimal("140.00"),
            stock_minimum=1,
            created_by="system",
            updated_by="system",
            active=True,
        )
        MovementInventory.objects.create(
            variant=self.variant_b,
            movement_type=MovementInventory.MovementType.PURCHASE,
            quantity=4,
            created_by="system",
        )
        self.product_c = Product.objects.create(
            name="Sandalia Riviera",
            brand="Costa",
            description="Tercer producto para relacionados",
            product_type="sandals",
            created_by="system",
            updated_by="system",
        )
        self.variant_c = ProductVariant.objects.create(
            product=self.product_c,
            gender="female",
            color="Beige",
            size="37",
            price=Decimal("179.90"),
            cost=Decimal("90.00"),
            stock_minimum=1,
            created_by="system",
            updated_by="system",
            active=True,
        )
        MovementInventory.objects.create(
            variant=self.variant_c,
            movement_type=MovementInventory.MovementType.PURCHASE,
            quantity=3,
            created_by="system",
        )

    def _checkout_as_customer(self, payload: dict):
        if "shipping_address" not in payload:
            payload = {
                **payload,
                "shipping_address": {
                    "department": "Cundinamarca",
                    "city": "Bogota",
                    "address_line1": "Calle 100 # 10-20",
                    "address_line2": "",
                    "reference": "Casa",
                    "postal_code": "110111",
                    "recipient_name": payload.get("customer_name") or "Cliente Test",
                    "recipient_phone": payload.get("customer_contact") or "3000000000",
                },
            }
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.post(reverse("store-checkout"), payload, format="json")
        self.client.force_authenticate(user=None)
        return response

    def test_store_products_list_is_public(self):
        response = self.client.get(reverse("store-products"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_PRODUCTS_OK")
        self.assertGreaterEqual(response.data["count"], 1)
        self.assertIn("page", response.data)
        self.assertIn("page_size", response.data)
        returned_products = response.data["products"]
        returned_names = [item["name"] for item in returned_products]
        self.assertIn(self.product.name, returned_names)
        target_product = next(item for item in returned_products if item["name"] == self.product.name)
        self.assertIsNotNone(target_product["image_url"])
        self.assertGreaterEqual(len(target_product["images"]), 1)

    def test_store_cart_validate_returns_total_and_items(self):
        payload = {"items": [{"variant_id": self.variant.id, "quantity": 2}]}

        response = self.client.post(reverse("store-cart-validate"), payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_CART_VALID")
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["total"], "399.80")
        self.assertIn("commercial", response.data)
        self.assertIn("is_viable_online", response.data["commercial"])

    def test_store_checkout_creates_pending_sale(self):
        payload = {
            "customer_name": "Cliente Web",
            "customer_contact": "3001231234",
            "items": [{"variant_id": self.variant.id, "quantity": 3}],
            "is_order": True,
        }

        response = self._checkout_as_customer(payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["code"], "STORE_CHECKOUT_CREATED")

        sale_id = response.data["order"]["sale_id"]
        sale = Sale.objects.get(id=sale_id)
        self.assertEqual(sale.status, "pending")
        self.assertEqual(sale.created_by, self.customer_user.username)
        self.assertEqual(sale.total, Decimal("599.70"))
        self.assertEqual(sale.details.count(), 1)
        self.assertEqual(sale.shipping_address.get("city"), "Bogota")
        self.assertIn("commercial", response.data)

    @override_settings(
        STORE_MARGIN_GUARD_ENABLED=True,
        STORE_MARGIN_MIN_PERCENT=Decimal("80"),
        STORE_MARGIN_WOMPI_PERCENT=Decimal("2.65"),
        STORE_MARGIN_WOMPI_FIXED_FEE=Decimal("700"),
        STORE_MARGIN_WOMPI_VAT_PERCENT=Decimal("19"),
        STORE_MARGIN_PACKAGING_COST=Decimal("1500"),
        STORE_MARGIN_RISK_PERCENT=Decimal("2"),
        STORE_MARGIN_DEFAULT_SHIPPING_COST=Decimal("12000"),
    )
    def test_store_checkout_blocks_when_margin_guard_fails(self):
        payload = {
            "customer_name": "Cliente Margen",
            "customer_contact": "3001231234",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
            "shipping_zone": "national",
            "estimated_weight_grams": 2000,
        }

        response = self._checkout_as_customer(payload)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "STORE_MARGIN_GUARD_BLOCKED")
        self.assertIn("commercial", response.data)

    def test_store_checkout_requires_authentication(self):
        payload = {
            "customer_name": "Cliente Web",
            "customer_contact": "3001231234",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
        }
        response = self.client.post(reverse("store-checkout"), payload, format="json")
        self.assertEqual(response.status_code, 401)

    def test_store_checkout_fails_if_stock_is_insufficient(self):
        payload = {
            "customer_name": "Cliente Web",
            "items": [{"variant_id": self.variant.id, "quantity": 99}],
        }

        response = self._checkout_as_customer(payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "STORE_CHECKOUT_FAILED")

    def test_store_products_pagination_and_ordering(self):
        response = self.client.get(f"{reverse('store-products')}?page=1&page_size=1&ordering=-name")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_PRODUCTS_OK")
        self.assertEqual(response.data["page"], 1)
        self.assertEqual(response.data["page_size"], 1)
        self.assertTrue(response.data["has_next"])
        self.assertEqual(len(response.data["products"]), 1)

    def test_store_featured_products_endpoint(self):
        response = self.client.get(reverse("store-featured-products"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_FEATURED_PRODUCTS_OK")
        self.assertGreaterEqual(response.data["count"], 1)

    def test_store_related_products_endpoint(self):
        response = self.client.get(reverse("store-related-products", args=[self.product.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_RELATED_PRODUCTS_OK")
        related_names = [item["name"] for item in response.data["products"]]
        self.assertIn(self.product_b.name, related_names)

    def test_store_order_status_with_contact(self):
        checkout_payload = {
            "customer_name": "Cliente Pedido",
            "customer_contact": "3115557788",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
        }
        checkout_response = self._checkout_as_customer(checkout_payload)
        sale_id = checkout_response.data["order"]["sale_id"]

        status_url = f"{reverse('store-order-status', args=[sale_id])}?customer_contact=3115557788"
        response = self.client.get(status_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_ORDER_STATUS_OK")
        self.assertEqual(response.data["order"]["sale_id"], sale_id)
        self.assertEqual(response.data["order"]["status"], "pending")
        self.assertEqual(len(response.data["order"]["items"]), 1)

    def test_store_order_status_requires_contact(self):
        response = self.client.get(reverse("store-order-status", args=[99999]))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "STORE_ORDER_CONTACT_REQUIRED")

    def test_store_order_lookup_by_sale_id(self):
        checkout_payload = {
            "customer_name": "Cliente Lookup ID",
            "customer_contact": "3000001000",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
        }
        checkout_response = self._checkout_as_customer(checkout_payload)
        sale_id = checkout_response.data["order"]["sale_id"]

        response = self.client.get(f"{reverse('store-order-lookup')}?sale_id={sale_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_ORDER_LOOKUP_OK")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["orders"][0]["sale_id"], sale_id)

    def test_store_order_lookup_by_customer_returns_multiple(self):
        for contact in ["3001002001", "3001002002"]:
            payload = {
                "customer_name": "Cliente Lookup",
                "customer_contact": contact,
                "items": [{"variant_id": self.variant.id, "quantity": 1}],
                "is_order": True,
            }
            self._checkout_as_customer(payload)

        response = self.client.get(
            f"{reverse('store-order-lookup')}?customer=Cliente Lookup&customer_contact=3001002"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_ORDER_LOOKUP_OK")
        self.assertGreaterEqual(response.data["count"], 2)

    def test_store_order_lookup_by_customer_requires_contact_hint(self):
        payload = {
            "customer_name": "Cliente Privado",
            "customer_contact": "3009898989",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
        }
        self._checkout_as_customer(payload)

        response = self.client.get(f"{reverse('store-order-lookup')}?customer=Cliente Privado")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "STORE_ORDER_LOOKUP_CONTACT_REQUIRED")

    def test_store_order_payment_confirms_payment_and_updates_status(self):
        checkout_payload = {
            "customer_name": "Cliente Pago",
            "customer_contact": "3005557788",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
        }
        checkout_response = self._checkout_as_customer(checkout_payload)
        sale_id = checkout_response.data["order"]["sale_id"]

        pay_payload = {
            "customer_contact": "3005557788",
            "payment_method": "nequi",
        }
        with self.settings(
            WOMPI_PUBLIC_KEY="pub_test_x",
            WOMPI_INTEGRITY_SECRET="int_test_x",
            WOMPI_REDIRECT_URL="http://localhost:8080/store/order-status",
        ):
            response = self.client.post(reverse("store-order-pay", args=[sale_id]), pay_payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_ORDER_PAYMENT_CHECKOUT_READY")
        self.assertEqual(response.data["order"]["status"], "pending")
        self.assertEqual(response.data["order"]["payment_status"], "pending")
        self.assertIsNotNone(response.data["order"]["payment_reference"])
        self.assertIn("checkout_url", response.data["payment"])
        self.assertIn("checkout.wompi.co", response.data["payment"]["checkout_url"])

    @patch("inventory.store.views.get_transaction")
    def test_store_wompi_verify_updates_order_to_paid(self, mock_get_transaction):
        checkout_payload = {
            "customer_name": "Cliente Verify",
            "customer_contact": "3001112222",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
        }
        checkout_response = self._checkout_as_customer(checkout_payload)
        sale_id = checkout_response.data["order"]["sale_id"]
        sale = Sale.objects.get(id=sale_id)
        sale.payment_reference = "ORD-VERIFY-123"
        sale.save(update_fields=["payment_reference"])

        mock_get_transaction.return_value = {
            "data": {
                "id": "tx_test_123",
                "status": "APPROVED",
                "reference": "ORD-VERIFY-123",
                "payment_method_type": "PSE",
            }
        }

        verify_payload = {
            "customer_contact": "3001112222",
            "transaction_id": "tx_test_123",
        }
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.post(reverse("store-order-wompi-verify", args=[sale_id]), verify_payload, format="json")
        self.client.force_authenticate(user=None)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_WOMPI_PAYMENT_SYNCED")
        self.assertEqual(response.data["order"]["status"], "paid")
        self.assertEqual(response.data["order"]["payment_status"], "paid")
        movement = MovementInventory.objects.filter(
            sale_id=sale_id,
            movement_type=MovementInventory.MovementType.SALE_OUT,
            variant_id=self.variant.id,
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, -1)

    @override_settings(
        STORE_SHIPPING_ENABLED=True,
        STORE_SHIPPING_AUTO_CREATE=True,
        STORE_SHIPPING_PROVIDER="mock",
        STORE_SHIPPING_CARRIER_NAME="TestCarrier",
        STORE_SHIPPING_SERVICES="eco:9000:72,express:15000:24",
    )
    @patch("inventory.store.views.get_transaction")
    def test_store_wompi_verify_creates_shipment_for_paid_order(self, mock_get_transaction):
        checkout_payload = {
            "customer_name": "Cliente Shipment",
            "customer_contact": "3002223333",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
        }
        checkout_response = self._checkout_as_customer(checkout_payload)
        sale_id = checkout_response.data["order"]["sale_id"]
        sale = Sale.objects.get(id=sale_id)
        sale.payment_reference = "ORD-SHIP-123"
        sale.save(update_fields=["payment_reference"])

        mock_get_transaction.return_value = {
            "data": {
                "id": "tx_ship_123",
                "status": "APPROVED",
                "reference": "ORD-SHIP-123",
                "payment_method_type": "CARD",
            }
        }

        verify_payload = {
            "customer_contact": "3002223333",
            "transaction_id": "tx_ship_123",
        }
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.post(reverse("store-order-wompi-verify", args=[sale_id]), verify_payload, format="json")
        self.client.force_authenticate(user=None)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["order"]["status"], "paid")
        shipment = Shipment.objects.filter(sale_id=sale_id).first()
        self.assertIsNotNone(shipment)
        self.assertEqual(shipment.carrier, "TestCarrier")
        self.assertEqual(shipment.service, "eco")

    @override_settings(
        STORE_SHIPPING_ENABLED=True,
        STORE_SHIPPING_AUTO_CREATE=True,
        STORE_SHIPPING_PROVIDER="http",
        STORE_SHIPPING_API_BASE_URL="https://shipping.example.com",
        STORE_SHIPPING_CREATE_PATH="/v1/shipments",
        STORE_SHIPPING_API_KEY="ship_key_123",
        STORE_SHIPPING_AUTH_HEADER="Authorization",
        STORE_SHIPPING_AUTH_PREFIX="Bearer ",
        STORE_SHIPPING_SERVICES="eco:9000:72,express:15000:24",
    )
    @patch("inventory.store.shipping._http_json")
    @patch("inventory.store.views.get_transaction")
    def test_store_wompi_verify_creates_http_provider_shipment(self, mock_get_transaction, mock_http_json):
        checkout_payload = {
            "customer_name": "Cliente Provider HTTP",
            "customer_contact": "3005550000",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
        }
        checkout_response = self._checkout_as_customer(checkout_payload)
        sale_id = checkout_response.data["order"]["sale_id"]
        sale = Sale.objects.get(id=sale_id)
        sale.payment_reference = "ORD-SHIP-HTTP-1"
        sale.save(update_fields=["payment_reference"])

        mock_get_transaction.return_value = {
            "data": {
                "id": "tx_ship_http_1",
                "status": "APPROVED",
                "reference": "ORD-SHIP-HTTP-1",
                "payment_method_type": "CARD",
            }
        }
        mock_http_json.return_value = {
            "data": {
                "id": "shp_123",
                "tracking_number": "TRK-HTTP-001",
                "label_url": "https://shipping.example.com/labels/TRK-HTTP-001.pdf",
                "carrier": "CarrierHTTP",
                "service": "eco",
                "shipping_cost": "8900",
                "currency": "COP",
                "status": "created",
            }
        }

        verify_payload = {
            "customer_contact": "3005550000",
            "transaction_id": "tx_ship_http_1",
        }
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.post(reverse("store-order-wompi-verify", args=[sale_id]), verify_payload, format="json")
        self.client.force_authenticate(user=None)

        self.assertEqual(response.status_code, 200)
        shipment = Shipment.objects.filter(sale_id=sale_id).first()
        self.assertIsNotNone(shipment)
        self.assertEqual(shipment.tracking_number, "TRK-HTTP-001")
        self.assertEqual(shipment.carrier, "CarrierHTTP")
        self.assertEqual(str(shipment.shipping_cost), "8900.00")

    @override_settings(STORE_SHIPPING_WEBHOOK_SECRET="ship_secret")
    def test_store_shipping_webhook_updates_status_and_is_idempotent(self):
        sale = Sale.objects.create(
            customer="Cliente Webhook",
            created_by="store_api",
            is_order=True,
            status="processing",
            payment_status="paid",
            total=Decimal("120.00"),
            confirmed_at=timezone.now() - timedelta(hours=3),
        )
        shipment = Shipment.objects.create(
            sale=sale,
            carrier="CarrierX",
            service="standard",
            tracking_number="TRK-ABC-123",
            provider_reference="PRV-123",
            shipping_cost=Decimal("10000"),
            currency="COP",
            status=Shipment.ShipmentStatus.IN_TRANSIT,
            created_by="test",
        )

        payload = {
            "event_id": "evt_ship_1",
            "event_type": "delivered",
            "tracking_number": shipment.tracking_number,
        }
        signature = shipping_webhook_signature(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            "ship_secret",
        )

        response = self.client.post(
            reverse("store-shipping-webhook"),
            payload,
            format="json",
            HTTP_X_STORE_SHIPPING_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_SHIPPING_WEBHOOK_OK")
        sale.refresh_from_db()
        shipment.refresh_from_db()
        self.assertEqual(sale.status, "delivered")
        self.assertEqual(shipment.status, Shipment.ShipmentStatus.DELIVERED)
        self.assertEqual(ShipmentEvent.objects.filter(provider_event_id="evt_ship_1").count(), 1)

        duplicate_response = self.client.post(
            reverse("store-shipping-webhook"),
            payload,
            format="json",
            HTTP_X_STORE_SHIPPING_SIGNATURE=signature,
        )
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(duplicate_response.data["code"], "STORE_SHIPPING_WEBHOOK_DUPLICATE")
        self.assertEqual(ShipmentEvent.objects.filter(provider_event_id="evt_ship_1").count(), 1)

    @override_settings(
        STORE_AUTO_ADVANCE_ENABLED=True,
        STORE_AUTO_TO_PROCESSING_MINUTES=0,
        STORE_AUTO_TO_SHIPPED_MINUTES=99999,
        STORE_AUTO_TO_DELIVERED_MINUTES=99999,
        STORE_AUTO_TO_COMPLETED_MINUTES=99999,
    )
    def test_auto_advance_command_moves_paid_to_processing(self):
        sale = Sale.objects.create(
            customer="Cliente Auto",
            created_by="store_api",
            is_order=True,
            status="paid",
            payment_status="paid",
            total=Decimal("100.00"),
            paid_at=timezone.now() - timedelta(minutes=10),
        )

        call_command("auto_advance_store_orders")

        sale.refresh_from_db()
        self.assertEqual(sale.status, "processing")
        self.assertIsNotNone(sale.confirmed_at)

    @override_settings(STORE_AUTO_ADVANCE_ENABLED=False)
    def test_auto_advance_command_respects_disabled_setting(self):
        sale = Sale.objects.create(
            customer="Cliente Auto Off",
            created_by="store_api",
            is_order=True,
            status="paid",
            payment_status="paid",
            total=Decimal("100.00"),
            paid_at=timezone.now() - timedelta(minutes=30),
        )

        call_command("auto_advance_store_orders")

        sale.refresh_from_db()
        self.assertEqual(sale.status, "paid")

    def test_store_order_status_includes_timeline_and_status_detail(self):
        checkout_payload = {
            "customer_name": "Cliente Timeline",
            "customer_contact": "3119990000",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
        }
        checkout_response = self._checkout_as_customer(checkout_payload)
        sale_id = checkout_response.data["order"]["sale_id"]

        response = self.client.get(
            f"{reverse('store-order-status', args=[sale_id])}?customer_contact=3119990000"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_ORDER_STATUS_OK")
        self.assertIn("status_detail", response.data["order"])
        self.assertIn("timeline", response.data["order"])
        self.assertGreaterEqual(len(response.data["order"]["timeline"]), 1)

    def test_store_ops_orders_list_requires_auth_and_returns_orders(self):
        unauth_response = self.client.get(reverse("store-ops-orders"))
        self.assertEqual(unauth_response.status_code, 401)

        self.client.force_authenticate(user=self.ops_user)
        auth_response = self.client.get(reverse("store-ops-orders"))
        self.assertEqual(auth_response.status_code, 200)
        self.assertEqual(auth_response.data["code"], "STORE_OPS_ORDERS_OK")
        self.assertIn("orders", auth_response.data)

    def test_store_ops_summary_reports_orders_missing_inventory_discount(self):
        sale = Sale.objects.create(
            customer="Cliente Riesgo Inventario",
            created_by="store_api",
            is_order=True,
            status="processing",
            payment_status="paid",
            total=Decimal("199.90"),
            paid_at=timezone.now() - timedelta(minutes=20),
            confirmed_at=timezone.now() - timedelta(minutes=10),
        )
        SaleDetail.objects.create(
            sale=sale,
            variant=self.variant,
            quantity=1,
            price=self.variant.price,
            subtotal=self.variant.price,
        )

        self.client.force_authenticate(user=self.ops_user)
        response = self.client.get(reverse("store-ops-summary"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_OPS_SUMMARY_OK")
        alerts = response.data["summary"]["inventory_alerts"]
        self.assertGreaterEqual(alerts["orders_without_stock_discount"], 1)
        self.assertIn(sale.id, alerts["affected_order_ids"])

    def test_store_ops_can_update_order_status(self):
        checkout_payload = {
            "customer_name": "Cliente Ops",
            "customer_contact": "3124445555",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
        }
        checkout_response = self._checkout_as_customer(checkout_payload)
        sale_id = checkout_response.data["order"]["sale_id"]

        self.client.force_authenticate(user=self.ops_user)
        response = self.client.patch(
            reverse("store-ops-order-status", args=[sale_id]),
            {"status": "paid", "note": "Pago validado en caja"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_OPS_ORDER_STATUS_UPDATED")
        self.assertEqual(response.data["order"]["status"], "paid")
        movement = MovementInventory.objects.filter(
            sale_id=sale_id,
            movement_type=MovementInventory.MovementType.SALE_OUT,
            variant_id=self.variant.id,
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, -1)

    def test_store_ops_can_register_manual_shipment(self):
        sale = Sale.objects.create(
            customer="Cliente Manual",
            created_by="store_api",
            is_order=True,
            status="paid",
            payment_status="paid",
            total=Decimal("150.00"),
            paid_at=timezone.now() - timedelta(minutes=10),
        )

        self.client.force_authenticate(user=self.ops_user)
        payload = {
            "carrier": "Servientrega",
            "tracking_number": "GUIA-001-ABC",
            "shipping_cost": "12000.00",
            "service": "mostrador",
            "status": "in_transit",
        }
        response = self.client.post(
            reverse("store-ops-order-shipment-manual", args=[sale.id]),
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_OPS_MANUAL_SHIPMENT_SAVED")
        sale.refresh_from_db()
        self.assertEqual(sale.status, "shipped")
        shipment = Shipment.objects.filter(sale_id=sale.id, tracking_number="GUIA-001-ABC").first()
        self.assertIsNotNone(shipment)
        self.assertEqual(shipment.carrier, "Servientrega")

    def test_store_ops_manual_shipment_rejects_duplicate_tracking(self):
        sale_a = Sale.objects.create(
            customer="Cliente A",
            created_by="store_api",
            is_order=True,
            status="paid",
            payment_status="paid",
            total=Decimal("80.00"),
            paid_at=timezone.now() - timedelta(minutes=5),
        )
        sale_b = Sale.objects.create(
            customer="Cliente B",
            created_by="store_api",
            is_order=True,
            status="paid",
            payment_status="paid",
            total=Decimal("90.00"),
            paid_at=timezone.now() - timedelta(minutes=5),
        )
        Shipment.objects.create(
            sale=sale_a,
            carrier="Interrapidisimo",
            service="mostrador",
            tracking_number="GUIA-DUP-123",
            shipping_cost=Decimal("10000"),
            currency="COP",
            status=Shipment.ShipmentStatus.IN_TRANSIT,
            created_by="storeops",
        )

        self.client.force_authenticate(user=self.ops_user)
        payload = {
            "carrier": "Servientrega",
            "tracking_number": "GUIA-DUP-123",
            "shipping_cost": "9500.00",
            "status": "in_transit",
        }
        response = self.client.post(
            reverse("store-ops-order-shipment-manual", args=[sale_b.id]),
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "STORE_OPS_MANUAL_SHIPMENT_DUPLICATE_TRACKING")

    def test_store_customer_register_and_login_endpoints(self):
        register_payload = {
            "username": "cliente_web_1",
            "email": "cliente1@web.com",
            "password": "secret1234",
            "first_name": "Cliente",
            "last_name": "Web",
        }

        register_response = self.client.post(reverse("store-customer-register"), register_payload, format="json")
        self.assertEqual(register_response.status_code, 201)
        self.assertEqual(register_response.data["code"], "STORE_CUSTOMER_REGISTERED")
        self.assertIn("access", register_response.data)
        self.assertIn("refresh", register_response.data)

        user = User.objects.get(username="cliente_web_1")
        self.assertTrue(user.groups.filter(name="Customers").exists())

        login_response = self.client.post(
            reverse("store-customer-login"),
            {"username": "cliente_web_1", "password": "secret1234"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.data["code"], "STORE_CUSTOMER_LOGIN_OK")
        self.assertIn("access", login_response.data)

    def test_store_checkout_uses_authenticated_user_as_creator(self):
        customers_group, _ = Group.objects.get_or_create(name="Customers")
        customer_user = User.objects.create_user(
            username="cliente_auth",
            email="cliente_auth@web.com",
            password="secret1234",
            is_staff=False,
        )
        customer_user.groups.add(customers_group)
        self.client.force_authenticate(user=customer_user)

        payload = {
            "customer_name": "Cliente Auth",
            "customer_contact": "3007770000",
            "items": [{"variant_id": self.variant.id, "quantity": 1}],
            "is_order": True,
            "shipping_address": {
                "department": "Antioquia",
                "city": "Medellin",
                "address_line1": "Carrera 50 # 10-30",
                "recipient_name": "Cliente Auth",
                "recipient_phone": "3007770000",
            },
        }
        response = self.client.post(reverse("store-checkout"), payload, format="json")

        self.assertEqual(response.status_code, 201)
        sale_id = response.data["order"]["sale_id"]
        sale = Sale.objects.get(id=sale_id)
        self.assertEqual(sale.created_by, "cliente_auth")

    def test_store_my_orders_returns_only_authenticated_customer_orders(self):
        customer_user = User.objects.create_user(
            username="cliente_orders",
            email="cliente_orders@web.com",
            password="secret1234",
            is_staff=False,
        )
        Sale.objects.create(
            customer="Cliente Orders",
            created_by="cliente_orders",
            is_order=True,
            total=Decimal("10.00"),
            status="pending",
            payment_status="unpaid",
        )
        Sale.objects.create(
            customer="Otro Cliente",
            created_by="store_api",
            is_order=True,
            total=Decimal("12.00"),
            status="pending",
            payment_status="unpaid",
        )

        self.client.force_authenticate(user=customer_user)
        response = self.client.get(reverse("store-my-orders"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_MY_ORDERS_OK")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["orders"][0]["payment_status"], "unpaid")

    @override_settings(
        WOMPI_PUBLIC_KEY="pub_test",
        WOMPI_INTEGRITY_SECRET="int_test",
        WOMPI_EVENTS_SECRET="evt_test",
        WOMPI_REDIRECT_URL="http://localhost:8080/store/order-status",
        WOMPI_API_BASE_URL="https://sandbox.wompi.co/v1",
    )
    def test_store_wompi_health_configured(self):
        response = self.client.get(reverse("store-wompi-health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_WOMPI_HEALTH_OK")
        self.assertTrue(response.data["configured"])
        self.assertEqual(response.data["environment"], "sandbox")
        self.assertEqual(response.data["missing"], [])

    @override_settings(
        WOMPI_PUBLIC_KEY="",
        WOMPI_INTEGRITY_SECRET="",
        WOMPI_EVENTS_SECRET="",
        WOMPI_REDIRECT_URL="",
    )
    def test_store_wompi_health_reports_missing_keys(self):
        response = self.client.get(reverse("store-wompi-health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_WOMPI_HEALTH_OK")
        self.assertFalse(response.data["configured"])
        self.assertIn("WOMPI_PUBLIC_KEY", response.data["missing"])
        self.assertIn("WOMPI_INTEGRITY_SECRET", response.data["missing"])

    def test_store_branding_public_endpoint(self):
        response = self.client.get(reverse("store-branding"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_BRANDING_OK")
        self.assertIn("branding", response.data)
        self.assertIn("store_name", response.data["branding"])

    def test_store_ops_branding_update(self):
        self.client.force_authenticate(user=self.ops_user)
        payload = {
            "store_name": "Golos Boutique",
            "tagline": "Estilo premium para cada paso",
            "logo_url": "https://example.com/logo.png",
            "hero_title": "Coleccion nueva 2026",
            "hero_subtitle": "Compra segura con entrega nacional",
        }
        response = self.client.patch(reverse("store-ops-branding"), payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "STORE_OPS_BRANDING_UPDATED")
        self.assertEqual(response.data["branding"]["store_name"], "Golos Boutique")
