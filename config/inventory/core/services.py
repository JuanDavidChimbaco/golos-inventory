"""
Servicios de negocio para Golos Inventory
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q, F
from django.utils.timezone import now
from datetime import date
from django.db.models.functions import TruncDate
from PIL import Image, UnidentifiedImageError
from ..models import MovementInventory, Sale, ProductImage, AuditLog, InventorySnapshot, ProductVariant, Supplier



def confirm_sale(sale_id: int, user) -> None:
    with transaction.atomic():
        # Traer la venta con bloqueo para evitar concurrentes
        sale = Sale.objects.select_for_update().get(id=sale_id)

        # Validaciones basicas
        if sale.status != "pending":
            raise ValidationError("La venta no está pendiente")

        # Traer los detalles de la venta
        details = sale.details.select_related("variant").all()
        if not details.exists():
            raise ValidationError("La venta no tiene Productos")

        # validar stock por variante
        for detail in details:
            if detail.variant.stock < detail.quantity:
                raise ValidationError(
                    f"Stock insuficiente para el producto {detail.variant.product.name}"
                )

        last_closed = (
            InventorySnapshot.objects
            .order_by("-month")
            .first()
        )

        if last_closed and sale.created_at.date() <= last_closed.month:
            raise ValidationError("No se pueden registrar movimientos en un mes cerrado")

        # confirmar venta
        sale.status = "completed"
        sale.created_by = user.username
        sale.save()

        # verificar si la venta ya fue procesada
        if MovementInventory.objects.filter(
            variant__in=[d.variant for d in details],
            movement_type="sale",
            observation=f"sale:{sale.id}"
        ).exists():
            raise ValidationError("Esta venta ya fue procesada")

        # crear movimientos
        movements = []
        for detail in details:
            movements.append(
                MovementInventory(
                    variant=detail.variant,
                    movement_type=MovementInventory.MovementType.SALE_OUT,
                    quantity=-detail.quantity,
                    created_by=user.username,
                    observation=f"sale:{sale.id}",
                )
            )


        MovementInventory.objects.bulk_create(movements)
        
        # registrar en auditoría
        AuditLog.objects.create(
            action="confirm_sale",
            entity="sale",
            entity_id=sale_id,
            performed_by=user.username,
            extra_data={
                "total_intems": details.count(),
                "total_amount": float(sale.total),
            },
        )


def daily_inventory_summary(start_date=None, end_date=None):
    qs = MovementInventory.objects.all()

    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    return (
        qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            total_in=Sum(
                "quantity",
                filter=Q(quantity__gt=0)
            ),
            total_out=Sum(
                "quantity",
                filter=Q(quantity__lt=0)
            ),
        )
        .annotate(
            balance=F("total_in") + F("total_out")  # Calcular balance
        )
        .order_by("day")
    )


def low_stock_variants():
    variants = ProductVariant.objects.annotate(
        current_stock=Sum("movements__quantity")
    )

    return variants.filter(
        current_stock__lte=F("stock_minimum")
    )


def create_monthly_snapshot(date=None):
    date = date or now().date().replace(day=1)

    variants = ProductVariant.objects.annotate(
        stock=Sum("movements__quantity")
    )

    snapshots = [
        InventorySnapshot(
            month=date,
            variant=v,
            stock=v.stock or 0
        )
        for v in variants
    ]

    InventorySnapshot.objects.bulk_create(
        snapshots,
        ignore_conflicts=True
    )


def inventory_history_queryset(filters):
    qs = MovementInventory.objects.select_related(
        "variant", "variant__product"
    ).order_by("created_at")

    if "product" in filters:
        qs = qs.filter(variant__product_id=filters["product"])

    return qs


def close_inventory_month(year: int, month: int) -> None:
    """
    Genera el snapshot de inventario para un mes específico
    """
    month_date = date(year, month, 1)

    today = date.today().replace(day=1)

    if month_date > today:
        raise ValidationError("No se puede cerrar un mes futuro")

    # Evitar duplicados
    if InventorySnapshot.objects.filter(month=month_date).exists():
        raise ValidationError("Este mes ya fue cerrado")

    with transaction.atomic():
        for variant in ProductVariant.objects.all():

            # Stock inicial = snapshot anterior o 0
            prev_snapshot = (
                InventorySnapshot.objects
                .filter(variant=variant, month__lt=month_date)
                .order_by("-month")
                .first()
            )

            stock_opening = prev_snapshot.stock_closing if prev_snapshot else 0

            # Movimientos del mes
            movements = MovementInventory.objects.filter(
                variant=variant,
                created_at__year=year,
                created_at__month=month,
            )

            total_in = movements.filter(quantity__gt=0).aggregate(
                total=Sum("quantity")
            )["total"] or 0

            total_out = movements.filter(quantity__lt=0).aggregate(
                total=Sum("quantity")
            )["total"] or 0

            stock_closing = stock_opening + total_in + total_out

            InventorySnapshot.objects.create(
                month=month_date,
                variant=variant,
                stock_opening=stock_opening,
                total_in=total_in,
                total_out=total_out,
                stock_closing=stock_closing,
            )

            # Registrar en auditoría
            AuditLog.objects.create(
                action="close_inventory_month",
                entity="inventory",
                entity_id=0,
                performed_by="system",  # o pásalo como parámetro
                extra_data={
                    "year": year,
                    "month": month,
                },
            )


def create_purchase(variant_id: int, quantity: int, unit_cost: float, supplier_id: int = None, supplier_name: str = "", user=None) -> MovementInventory:
    """
    Crear movimiento de compra (entrada de inventario)
    
    Args:
        variant_id: ID de la variante de producto
        quantity: Cantidad comprada (debe ser positiva)
        unit_cost: Costo unitario del producto
        supplier_id: ID del proveedor (opcional)
        supplier_name: Nombre del proveedor (si no hay ID)
        user: Usuario que realiza la acción
    
    Returns:
        MovementInventory: Movimiento creado
    
    Raises:
        ValidationError: Si la cantidad es negativa o cero
    """
    if quantity <= 0:
        raise ValidationError("La cantidad de compra debe ser mayor a cero")
    
    if unit_cost <= 0:
        raise ValidationError("El costo unitario debe ser mayor a cero")
    
    # Validar que la variante exista
    try:
        variant = ProductVariant.objects.get(id=variant_id)
    except ProductVariant.DoesNotExist:
        raise ValidationError("La variante de producto no existe")
    
    # Obtener proveedor si se especificó ID
    supplier = None
    if supplier_id:
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            supplier_name = supplier.name
        except Supplier.DoesNotExist:
            raise ValidationError("El proveedor no existe")
    
    with transaction.atomic():
        # Crear movimiento de compra
        movement = MovementInventory.objects.create(
            variant=variant,
            quantity=quantity,  # Positivo = entrada
            movement_type=MovementInventory.MovementType.PURCHASE,
            observation=f"Compra - Proveedor: {supplier_name}" if supplier_name else "Compra directa",
            supplier=supplier,
            created_by=user.username if user else "system",
        )
        
        # Actualizar datos del proveedor si existe
        if supplier:
            supplier.last_purchase_date = now().date()
            supplier.save()
        
        # Registrar en auditoría
        AuditLog.objects.create(
            action="create_purchase",
            entity="movement_inventory",
            entity_id=movement.id,
            performed_by=user.username if user else "system",
            extra_data={
                "variant_id": variant_id,
                "quantity": quantity,
                "unit_cost": float(unit_cost),
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "product_name": variant.product.name,
            },
        )
        
        return movement


def create_adjustment(variant_id: int, quantity: int, reason: str, user=None) -> MovementInventory:
    """
    Crear ajuste de inventario (corrección manual)
    
    Args:
        variant_id: ID de la variante de producto
        quantity: Cantidad a ajustar (positiva = entrada, negativa = salida)
        reason: Motivo del ajuste (requerido)
        user: Usuario que realiza la acción
    
    Returns:
        MovementInventory: Movimiento creado
    
    Raises:
        ValidationError: Si no se proporciona motivo
    """
    if not reason or not reason.strip():
        raise ValidationError("El motivo del ajuste es requerido")
    
    # Validar que la variante exista
    try:
        variant = ProductVariant.objects.get(id=variant_id)
    except ProductVariant.DoesNotExist:
        raise ValidationError("La variante de producto no existe")
    
    with transaction.atomic():
        # Crear movimiento de ajuste
        movement = MovementInventory.objects.create(
            variant=variant,
            quantity=quantity,  # Puede ser positivo o negativo
            movement_type=MovementInventory.MovementType.ADJUSTMENT,
            observation=f"Ajuste: {reason}",
            created_by=user.username if user else "system",
        )
        
        # Registrar en auditoría
        AuditLog.objects.create(
            action="create_adjustment",
            entity="movement_inventory",
            entity_id=movement.id,
            performed_by=user.username if user else "system",
            extra_data={
                "variant_id": variant_id,
                "quantity": quantity,
                "reason": reason,
                "product_name": variant.product.name,
            },
        )
        
        return movement


def create_sale_return(sale_id: int, items: list, reason: str, user=None) -> list:
    """
    Crear devolución de venta (entrada de inventario)
    
    Args:
        sale_id: ID de la venta original
        items: Lista de items a devolver [{'sale_detail_id': 1, 'quantity': 2}]
        reason: Motivo de la devolución
        user: Usuario que realiza la acción
    
    Returns:
        list: Movimientos creados
    
    Raises:
        ValidationError: Si la venta no existe o no está completada
    """
    # Validar venta
    try:
        sale = Sale.objects.get(id=sale_id)
    except Sale.DoesNotExist:
        raise ValidationError("La venta no existe")
    
    if sale.status != "completed":
        raise ValidationError("Solo se pueden devolver ventas completadas")
    
    movements_created = []
    
    with transaction.atomic():
        for item in items:
            sale_detail_id = item.get('sale_detail_id')
            quantity = item.get('quantity')
            
            # Validar detalle de venta
            try:
                detail = SaleDetail.objects.get(id=sale_detail_id, sale=sale)
            except SaleDetail.DoesNotExist:
                raise ValidationError(f"El detalle de venta {sale_detail_id} no existe")
            
            if quantity <= 0:
                raise ValidationError("La cantidad a devolver debe ser mayor a cero")
            
            if quantity > detail.quantity:
                raise ValidationError(f"No se pueden devolver más de {detail.quantity} unidades")
            
            # Crear movimiento de devolución
            movement = MovementInventory.objects.create(
                variant=detail.variant,
                quantity=quantity,  # Positivo = entrada
                movement_type=MovementInventory.MovementType.SALE_RETURN,
                observation=f"Devolución venta #{sale.id} - {reason}",
                created_by=user.username if user else "system",
            )
            
            movements_created.append(movement)
            
            # Registrar en auditoría
            AuditLog.objects.create(
                action="create_sale_return",
                entity="movement_inventory",
                entity_id=movement.id,
                performed_by=user.username if user else "system",
                extra_data={
                    "sale_id": sale_id,
                    "sale_detail_id": sale_detail_id,
                    "quantity": quantity,
                    "reason": reason,
                    "product_name": detail.variant.product.name,
                },
            )
        
        return movements_created


def create_supplier_return(variant_id: int, quantity: int, reason: str, supplier_id: int = None, supplier_name: str = "", user=None) -> MovementInventory:
    """
    Crear devolución a proveedor (salida de inventario)
    
    Args:
        variant_id: ID de la variante de producto
        quantity: Cantidad a devolver (debe ser positiva)
        reason: Motivo de la devolución
        supplier_id: ID del proveedor (opcional)
        supplier_name: Nombre del proveedor (si no hay ID)
        user: Usuario que realiza la acción
    
    Returns:
        MovementInventory: Movimiento creado
    
    Raises:
        ValidationError: Si la cantidad es negativa o no hay stock suficiente
    """
    if quantity <= 0:
        raise ValidationError("La cantidad a devolver debe ser mayor a cero")
    
    if not reason or not reason.strip():
        raise ValidationError("El motivo de la devolución es requerido")
    
    # Validar que la variante exista
    try:
        variant = ProductVariant.objects.get(id=variant_id)
    except ProductVariant.DoesNotExist:
        raise ValidationError("La variante de producto no existe")
    
    # Obtener proveedor si se especificó ID
    supplier = None
    if supplier_id:
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            supplier_name = supplier.name
        except Supplier.DoesNotExist:
            raise ValidationError("El proveedor no existe")
    
    # Validar stock disponible
    current_stock = variant.stock
    if current_stock < quantity:
        raise ValidationError(f"Stock insuficiente. Actual: {current_stock}, Requerido: {quantity}")
    
    with transaction.atomic():
        # Crear movimiento de devolución a proveedor
        movement = MovementInventory.objects.create(
            variant=variant,
            quantity=-quantity,  # Negativo = salida
            movement_type=MovementInventory.MovementType.RETURN,
            observation=f"Devolución proveedor {supplier_name} - {reason}" if supplier_name else f"Devolución proveedor - {reason}",
            supplier=supplier,
            created_by=user.username if user else "system",
        )
        
        # Registrar en auditoría
        AuditLog.objects.create(
            action="create_supplier_return",
            entity="movement_inventory",
            entity_id=movement.id,
            performed_by=user.username if user else "system",
            extra_data={
                "variant_id": variant_id,
                "quantity": quantity,
                "reason": reason,
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "product_name": variant.product.name,
                "current_stock": current_stock,
            },
        )
        
        return movement


class ImageService:
    """Servicio para procesamiento y gestión de imágenes de productos"""
    
    # Constantes de configuración
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB en bytes
    ALLOWED_FORMATS = ['JPEG', 'PNG', 'WEBP']
    MAX_DIMENSIONS = (1200, 1200)  # Máximo 1200x1200px
    
    @classmethod
    def validate_image_file(cls, image_file):
        """
        Valida que el archivo de imagen cumpla con los requisitos
        
        Args:
            image_file: Archivo de imagen a validar
            
        Raises:
            ValidationError: Si la imagen no cumple los requisitos
        """
        # Validar tamaño del archivo
        if image_file.size > cls.MAX_FILE_SIZE:
            raise ValidationError(
                f"La imagen es demasiado grande. "
                f"Máximo permitido: {cls.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Validar formato de imagen
        # Abre la imagen en modo solo lectura para evitar modificaciones no intencionadas
        try:
            with Image.open(image_file) as img:
                # Verifica que el formato de la imagen sea válido
                if img.format.upper() not in map(str.upper, cls.ALLOWED_FORMATS):
                    raise ValidationError(
                        f"Formato de imagen no permitido. Formatos válidos: {', '.join(cls.ALLOWED_FORMATS)}"
                    )
        except UnidentifiedImageError as e:
            # Si no se puede abrir como imagen, considera que no es una imagen válida
            raise ValidationError(f"El archivo no es una imagen válida: {str(e)}")
    
    @classmethod
    def extract_image_metadata(cls, image_file):
        """
        Extrae metadatos de la imagen
        
        Args:
            image_file: Archivo de imagen
            
        Returns:
            dict: Metadatos de la imagen (size, width, height, format)
        """
        try:
            img = Image.open(image_file)
            return {
                'file_size': image_file.size,
                'width': img.width,
                'height': img.height,
                'format': img.format
            }
        except Exception:
            return {
                'file_size': image_file.size,
                'width': 0,
                'height': 0,
                'format': 'Unknown'
            }
    
    @classmethod
    def process_product_image(cls, product_image_instance):
        """
        Procesa una imagen de producto: valida y extrae metadatos
        
        Args:
            product_image_instance: Instancia de ProductImage a procesar
            
        Returns:
            ProductImage: Instancia actualizada con metadatos
        """
        # Validar la imagen
        cls.validate_image_file(product_image_instance.image)
        
        # Extraer metadatos
        metadata = cls.extract_image_metadata(product_image_instance.image)
        
        # Actualizar instancia con metadatos
        product_image_instance.file_size = metadata['file_size']
        product_image_instance.width = metadata['width']
        product_image_instance.height = metadata['height']
        
        return product_image_instance
    
    @classmethod
    def set_primary_image(cls, product, image_id):
        """
        Establece una imagen como principal del producto
        
        Args:
            product: Instancia de Product
            image_id: ID de la imagen a establecer como principal
        """
        with transaction.atomic():
            # Quitar primary a todas las imágenes del producto
            ProductImage.objects.filter(product=product).update(is_primary=False)
            
            # Establecer la nueva imagen como primary
            ProductImage.objects.filter(id=image_id, product=product).update(is_primary=True)
