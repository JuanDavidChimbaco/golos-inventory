from django.db import models

# Create your models here.


class Product(models.Model):
    """Producto base

    Attributes:
        name (CharField): Nombre del producto
        brand (CharField): Marca del producto
        description (TextField): Descripción del producto
        active (BooleanField): Estado del producto
        created_at (DateTimeField): Fecha de creación
        updated_at (DateTimeField): Fecha de actualización
        created_by (CharField): Usuario que creó el producto
        updated_by (CharField): Usuario que actualizó el producto
    """

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=50)  # mientras se usa user
    updated_by = models.CharField(max_length=50)  # mientras se usa user

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
    image = models.ImageField(upload_to="products/")
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

    def __str__(self):
        return f"Variant of {self.product.name} - {self.color} - {self.size}"

    class Meta:
        unique_together = ("product", "gender", "color", "size")


class MovementInventory(models.Model):
    """Movimiento de inventario

    Attributes:
        variant (ForeignKey): Variante de producto al que pertenece el movimiento
        movement_type (CharField): Tipo de movimiento
        quantity (PositiveIntegerField): Cantidad del movimiento
        observation (TextField): Observación del movimiento
        created_at (DateTimeField): Fecha de creación
        created_by (CharField): Usuario que creó el movimiento
    """

    variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="movements"
    )
    movement_type = models.CharField(
        max_length=50,
        choices=[
            ("purchase", "Purchase"),
            ("sale", "Sale"),
            ("adjustment", "Adjustment"),
            ("return", "Return"),
        ],
    )
    quantity = models.IntegerField()
    observation = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=50)

    def __str__(self):
        return f"Movement of {self.variant.product.name} - {self.movement_type} {self.quantity}"


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
            ("completed", "Completed"),
            ("canceled", "Canceled"),
        ],
        default="pending",
    )
    is_order = models.BooleanField(default=False)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    active = models.BooleanField(default=True)

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
        return f"Detail of {self.sales} - {self.variant.product.name} x {self.quantity}"

    class Meta:
        unique_together = ("sale", "variant")
