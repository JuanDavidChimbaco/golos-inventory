from django.db import models
from django.db.models import Sum
from storages.backends.s3boto3 import S3Boto3Storage


# Create your models here.


class Supplier(models.Model):
    """Proveedor simple para negocio informal
    
    Attributes:
        name (CharField): Nombre del proveedor
        phone (CharField): Teléfono (opcional)
        address (TextField): Dirección (opcional)
        nit (CharField): NIT (opcional, para proveedores formales)
        preferred_products (ManyToManyField): Productos que suele vender
        average_price (DecimalField): Precio promedio de sus productos
        last_purchase_date (DateField): Última fecha de compra
        is_active (BooleanField): Sigue existiendo
        created_at (DateTimeField): Fecha de creación
        updated_at (DateTimeField): Fecha de actualización
        created_by (CharField): Usuario que creó el proveedor
    """
    
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    nit = models.CharField(max_length=20, blank=True, null=True)
    
    # Datos útiles para el negocio
    preferred_products = models.ManyToManyField(
        'Product', 
        related_name='suppliers',
        blank=True,
        help_text="Productos que este proveedor suele vender"
    )
    average_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Precio promedio de sus productos"
    )
    last_purchase_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Última fecha de compra"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=50)

    class Meta:
        permissions = [
            ("manage_suppliers", "Can manage suppliers"),
        ]
        ordering = ["-last_purchase_date", "name"]

    def __str__(self):
        return self.name

    def get_total_purchases(self):
        """Obtener total de compras a este proveedor"""
        # Implementaremos cuando creemos el modelo Purchase
        return 0


class Product(models.Model):
    """Producto base

    Attributes:
        name (CharField): Nombre del producto
        brand (CharField): Marca del producto
        description (TextField): Descripción del producto
        product_type (CharField): Tipo de producto (para zapatos)
        active (BooleanField): Estado del producto
        created_at (DateTimeField): Fecha de creación
        updated_at (DateTimeField): Fecha de actualización
        created_by (CharField): Usuario que creó el producto
        updated_by (CharField): Usuario que actualizó el producto
    """

    PRODUCT_TYPES = [
        ('sneakers', 'Tenis'),
        ('heels', 'Tacones'),
        ('classics', 'Clásicos'),
        ('boots', 'Botas'),
        ('sandals', 'Sandalias'),
        ('flats', 'Planas'),
        ('loafers', 'Mocasines'),
        ('other', 'Otro'),
    ]

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPES,
        default='sneakers',
        help_text="Tipo de producto (especialmente para zapatos)"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=50)  # mientras se usa user
    updated_by = models.CharField(max_length=50)  # mientras se usa user

    class Meta:
        permissions = [
            # Permisos personalizados únicos (los demás son creados automáticamente por Django)
            ("confirm_sale", "Can confirm sales"),
            ("manage_inventory", "Can manage inventory"),
        ]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """Imagen de producto

    Attributes:
        product (ForeignKey): Producto al que pertenece la imagen
        image (ImageField): Imagen del producto
        is_primary (BooleanField): Si es la imagen principal del producto
        alt_text (CharField): Texto alternativo para accesibilidad y SEO
        file_size (IntegerField): Tamaño del archivo en bytes (autocompletado)
        width (IntegerField): Ancho de la imagen en píxeles (autocompletado)
        height (IntegerField): Alto de la imagen en píxeles (autocompletado)
        created_at (DateTimeField): Fecha de creación
        updated_at (DateTimeField): Fecha de actualización
        created_by (CharField): Usuario que creó la imagen
        updated_by (CharField): Usuario que actualizó la imagen
    """

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="images"
    )
    variant = models.ForeignKey(
        'ProductVariant', on_delete=models.SET_NULL, null=True, blank=True, related_name="images"
    )
    image = models.ImageField(
        upload_to="products/",
        storage=S3Boto3Storage(),
        help_text="Imagen del producto almacenada en Backblaze"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Marcar como imagen principal del producto"
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Texto alternativo para SEO y accesibilidad"
    )
    # Campos autocompletados por el servicio
    file_size = models.IntegerField(
        null=True, blank=True, editable=False,
        help_text="Tamaño del archivo en bytes (autocompletado)"
    )
    width = models.IntegerField(
        null=True, blank=True, editable=False,
        help_text="Ancho en píxeles (autocompletado)"
    )
    height = models.IntegerField(
        null=True, blank=True, editable=False,
        help_text="Alto en píxeles (autocompletado)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=50)  # mientras se usa user
    updated_by = models.CharField(max_length=50)  # mientras se usa user

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductVariant(models.Model):
    """Variante de producto

    Attributes:
        product (ForeignKey): Producto al que pertenece la variante
        gender (CharField): Género de la variante
        color (CharField): Color de la variante
        size (CharField): Tamaño de la variante
        price (DecimalField): Precio de la variante
        cost (DecimalField): Costo de la variante
        stock_minimum (PositiveIntegerField): Stock mínimo de la variante
        active (BooleanField): Estado de la variante
        created_at (DateTimeField): Fecha de creación
        updated_at (DateTimeField): Fecha de actualización
        created_by (CharField): Usuario que creó la variante
        updated_by (CharField): Usuario que actualizó la variante
    """

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="variants"
    )
    gender = models.CharField(
        max_length=10,
        choices=[("male", "Male"), ("female", "Female"), ("unisex", "Unisex")],
    )
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    stock_minimum = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=50)  # mientras se usa user
    updated_by = models.CharField(max_length=50)  # mientras se usa user
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Variant of {self.product.name} - {self.color} - {self.size}"

    class Meta:
        unique_together = ("product", "gender", "color", "size")
    
    @property
    def stock(self):
        return self.movements.aggregate(
            total=Sum("quantity")
        )["total"] or 0


class Sale(models.Model):
    """Venta

    Attributes:
        customer (CharField): Cliente de la venta
        created_at (DateTimeField): Fecha de creación
        created_by (CharField): Usuario que creó la venta
        status (CharField): Estado de la venta
        is_order (BooleanField): Si es una orden
        total (DecimalField): Total de la venta
        active (BooleanField): Estado de la venta
    """

    customer = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("processing", "Processing"),
            ("shipped", "Shipped"),
            ("delivered", "Delivered"),
            ("completed", "Completed"),
            ("canceled", "Canceled"),
        ],
        default="pending",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("unpaid", "Unpaid"),
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
        default="unpaid",
    )
    payment_method = models.CharField(max_length=30, blank=True, null=True)
    payment_reference = models.CharField(max_length=80, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    status_notes = models.TextField(blank=True, null=True)
    is_order = models.BooleanField(default=False)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            # Permisos personalizados únicos (los demás son creados automáticamente por Django)
            ("confirm_sale", "Can confirm sales"),
        ]

    def __str__(self):
        return f"Sale to {self.customer} - {self.status}"


class SaleDetail(models.Model):
    """Detalle de venta

    Attributes:
        sale (ForeignKey): Venta a la que pertenece el detalle
        variant (ForeignKey): Variante de producto del detalle
        quantity (PositiveIntegerField): Cantidad del detalle
        price (DecimalField): Precio del detalle
        subtotal (DecimalField): Subtotal del detalle
    """

    sale = models.ForeignKey(
        Sale, on_delete=models.PROTECT, related_name="details"
    )  # por ahora mientras se diseña un cliente
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Detail of {self.sale} - {self.variant.product.name} x {self.quantity}"

    class Meta:
        unique_together = ("sale", "variant")


class MovementInventory(models.Model):
    """Movimiento de inventario

    Attributes:
        variant (ForeignKey): Variante de producto al que pertenece el movimiento
        movement_type (CharField): Tipo de movimiento (compra, venta, ajuste, devolución)
        quantity (PositiveIntegerField): Cantidad del movimiento
        observation (TextField): Observación del movimiento
        supplier (ForeignKey): Proveedor (opcional, para compras y devoluciones)
        created_at (DateTimeField): Fecha de creación
        created_by (CharField): Usuario que creó el movimiento
    """
    class MovementType(models.TextChoices):
        """Tipos de movimiento de inventario"""
        
        PURCHASE = "purchase", "Compra"
        SALE_OUT = "sale_out", "Salida por venta"
        SALE_RETURN = "sale_return", "Devolución de venta"
        ADJUSTMENT = "adjustment", "Ajuste"
        RETURN = "return", "Devolución proveedor"

    variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="movements"
    )
    sale = models.ForeignKey(
        Sale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_movements",
        help_text="Venta relacionada (para salidas y devoluciones)"
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices
    )
    quantity = models.IntegerField()
    observation = models.TextField(blank=True, null=True)
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="movements",
        help_text="Proveedor (para compras y devoluciones)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=50)

    class Meta:
        permissions = [
            # Permisos personalizados únicos (los demás son creados automáticamente por Django)
            ("manage_inventory", "Can manage inventory"),
        ]

    def __str__(self):
        return f"Movement of {self.variant.product.name} - {self.movement_type} {self.quantity}"


class AuditLog(models.Model):
    """
    Log de auditoría para rastrear acciones realizadas en el sistema
    """
    action = models.CharField(max_length=100)
    entity = models.CharField(max_length=100)
    entity_id = models.PositiveIntegerField()
    performed_by = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    extra_data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.action} - {self.entity} ({self.entity_id})"


class InventorySnapshot(models.Model):
    """
    Snapshot mensual del inventario por variante
    """
    month = models.DateField()  # Siempre usar el primer día del mes
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="snapshots"
    )

    stock_opening = models.IntegerField()
    total_in = models.IntegerField()
    total_out = models.IntegerField()
    stock_closing = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("month", "variant")
        ordering = ["-month", "variant"]

    def __str__(self):
        return f"{self.variant} - {self.month} ({self.stock_closing})"


class StoreBranding(models.Model):
    """
    Configuracion visual publica de la tienda online.
    """

    store_name = models.CharField(max_length=120, default="Mi Tienda")
    tagline = models.CharField(max_length=180, blank=True, default="")
    logo_url = models.URLField(blank=True, null=True)
    hero_title = models.CharField(max_length=140, blank=True, default="")
    hero_subtitle = models.CharField(max_length=220, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=50, blank=True, default="system")

    class Meta:
        verbose_name = "Store Branding"
        verbose_name_plural = "Store Branding"

    def __str__(self):
        return self.store_name
