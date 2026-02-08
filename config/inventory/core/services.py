"""
Servicios de negocio para Golos Inventory
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q, F
from django.utils.timezone import now
from datetime import date
from django.db.models.functions import TruncDate
from ..models import MovementInventory, Sale, ProductImage, AuditLog, InventorySnapshot, ProductVariant



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
        stock=Sum("movements__quantity")
    )

    return variants.filter(
        stock__lte=F("stock_minimum")
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
        try:
            img = Image.open(image_file)
            if img.format not in cls.ALLOWED_FORMATS:
                raise ValidationError(
                    f"Formato no permitido. Formatos válidos: {', '.join(cls.ALLOWED_FORMATS)}"
                )
        except Exception:
            raise ValidationError("El archivo no es una imagen válida")
    
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
