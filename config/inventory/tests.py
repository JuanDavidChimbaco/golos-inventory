from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from PIL import Image
from io import BytesIO
from .models import Product, ProductVariant, MovementInventory, Sale, SaleDetail, ProductImage, Supplier
from .core.services import confirm_sale, ImageService


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
