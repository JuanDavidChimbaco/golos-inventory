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
from io import BytesIO
from ..models import MovementInventory, Sale, SaleDetail, ProductImage, AuditLog, InventorySnapshot, ProductVariant, Supplier



class SaleService:
    """Servicios para gestión de ventas"""
    
    @staticmethod
    def _validate_sale_for_confirmation(sale: Sale) -> None:
        """Valida que una venta puede ser confirmada"""
        if sale.status != "pending":
            raise ValidationError("La venta no está pendiente")
        
        # Traer los detalles de la venta
        details = sale.details.select_related("variant").all()
        if not details.exists():
            raise ValidationError("La venta no tiene Productos")
        
        for detail in details:
            # 1. Validar Soft Delete (Integridad)
            if detail.variant.is_deleted:
                raise ValidationError(
                    f"El producto {detail.variant} ha sido eliminado y no puede venderse."
                )
            # 2. Validar Stock (Disponibilidad)
            if detail.variant.stock < detail.quantity:
                raise ValidationError(
                    f"Stock insuficiente para {detail.variant.product.name}. "
                    f"Disponible: {detail.variant.stock}, Requerido: {detail.quantity}"
                )
        
        # Validar mes cerrado
        last_closed = (
            InventorySnapshot.objects
            .order_by("-month")
            .first()
        )
        
        if last_closed and sale.created_at.date() <= last_closed.month:
            raise ValidationError("No se pueden registrar movimientos en un mes cerrado")
    
    @staticmethod
    def _create_sale_movements(sale: Sale, user) -> list:
        """Crea los movimientos de inventario vinculados a la venta"""
    
        # 1. Verificar duplicados usando la FK (mucho más eficiente que buscar en texto)
        if MovementInventory.objects.filter(
            sale=sale, 
            movement_type=MovementInventory.MovementType.SALE_OUT
        ).exists():
            raise ValidationError("Esta venta ya tiene movimientos de salida registrados")
        
        details = sale.details.select_related("variant").all()
        movements = []
        
        for detail in details:
            movements.append(
                MovementInventory(
                    variant=detail.variant,
                    sale=sale,  # <--- Vinculamos la venta directamente
                    movement_type=MovementInventory.MovementType.SALE_OUT,
                    quantity=-detail.quantity,
                    created_by=user.username,
                    observation=f"Salida por venta #{sale.id}",
                )
            )
        
        return MovementInventory.objects.bulk_create(movements)
    
    @staticmethod
    def _log_sale_confirmation(sale: Sale, user) -> None:
        """Registra en auditoría la confirmación de venta"""
        details = sale.details.select_related("variant").all()
        AuditLog.objects.create(
            action="confirm_sale",
            entity="sale",
            entity_id=sale.id,
            performed_by=user.username,
            extra_data={
                "total_items": details.count(),
                "total_amount": float(sale.total),
            },
        )
    
    @classmethod
    def confirm_sale(cls, sale_id: int, user) -> None:
        """Confirma una venta y actualiza el inventario"""
        with transaction.atomic():
            # Traer la venta con bloqueo para evitar concurrentes
            sale = Sale.objects.select_for_update().get(id=sale_id)
            
            # Validaciones
            cls._validate_sale_for_confirmation(sale)
            
            # Confirmar venta
            sale.status = "completed"
            sale.created_by = user.username
            sale.save()
            
            # Crear movimientos
            cls._create_sale_movements(sale, user)
            
            # Registrar auditoría
            cls._log_sale_confirmation(sale, user)


# Función de compatibilidad - mantener la interfaz original
def confirm_sale(sale_id: int, user) -> None:
    """Función de compatibilidad para confirm_sale"""
    return SaleService.confirm_sale(sale_id, user)


class ReportingService:
    """Servicios para reportes y consultas de inventario"""
    
    @staticmethod
    def daily_inventory_summary(start_date=None, end_date=None):
        """Genera resumen diario de movimientos de inventario"""
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
                balance=F("total_in") + F("total_out")
            )
            .order_by("day")
        )
    
    @staticmethod
    def low_stock_variants():
        """Retorna variantes con stock bajo"""
        variants = ProductVariant.objects.annotate(
            current_stock=Sum("movements__quantity")
        )
        
        return variants.filter(
            current_stock__lte=F("stock_minimum"),
            is_deleted=False
        )
    
    @staticmethod
    def create_monthly_snapshot(date=None):
        """Crea snapshot mensual de inventario"""
        snapshot_date = date or now().date().replace(day=1)
        
        variants = ProductVariant.objects.annotate(
            stock=Sum("movements__quantity")
        )
        
        snapshots = [
            InventorySnapshot(
                month=snapshot_date,
                variant=v,
                stock=v.stock or 0
            )
            for v in variants
        ]
        
        InventorySnapshot.objects.bulk_create(
            snapshots,
            ignore_conflicts=True
        )
    
    @staticmethod
    def inventory_history_queryset(filters):
        """Genera queryset para historial de inventario con filtros"""
        qs = MovementInventory.objects.select_related(
            "variant", "variant__product"
        ).order_by("created_at")
        
        if "product" in filters:
            qs = qs.filter(variant__product_id=filters["product"])
        
        return qs


# Funciones de compatibilidad - mantener la interfaz original
def daily_inventory_summary(start_date=None, end_date=None):
    """Función de compatibilidad para daily_inventory_summary"""
    return ReportingService.daily_inventory_summary(start_date, end_date)

def low_stock_variants():
    """Función de compatibilidad para low_stock_variants"""
    return ReportingService.low_stock_variants()

def create_monthly_snapshot(date=None):
    """Función de compatibilidad para create_monthly_snapshot"""
    return ReportingService.create_monthly_snapshot(date)

def inventory_history_queryset(filters):
    """Función de compatibilidad para inventory_history_queryset"""
    return ReportingService.inventory_history_queryset(filters)


class MovementService:
    """Servicios para gestión de movimientos de inventario"""
    
    @staticmethod
    def _validate_variant_exists(variant_id: int) -> ProductVariant:
        """Valida que la variante exista y la retorna"""
        try:
            return ProductVariant.objects.get(id=variant_id)
        except ProductVariant.DoesNotExist:
            raise ValidationError("La variante de producto no existe")
    
    @staticmethod
    def _get_supplier(supplier_id: int = None, supplier_name: str = "") -> tuple:
        """Obtiene el proveedor y retorna (supplier, supplier_name)"""
        supplier = None
        if supplier_id:
            try:
                supplier = Supplier.objects.get(id=supplier_id)
                supplier_name = supplier.name
            except Supplier.DoesNotExist:
                raise ValidationError("El proveedor no existe")
        return supplier, supplier_name
    
    @staticmethod
    def _log_movement(action: str, movement: MovementInventory, extra_data: dict, user=None) -> None:
        """Registra en auditoría un movimiento"""
        AuditLog.objects.create(
            action=action,
            entity="movement_inventory",
            entity_id=movement.id,
            performed_by=user.username if user else "system",
            extra_data=extra_data,
        )
    
    @classmethod
    def create_purchase(cls, variant_id: int, quantity: int, unit_cost: float, 
                       supplier_id: int = None, supplier_name: str = "", user=None) -> MovementInventory:
        """Crear movimiento de compra (entrada de inventario)"""
        if quantity <= 0:
            raise ValidationError("La cantidad de compra debe ser mayor a cero")
        
        if unit_cost <= 0:
            raise ValidationError("El costo unitario debe ser mayor a cero")
        
        variant = cls._validate_variant_exists(variant_id)
        supplier, supplier_name = cls._get_supplier(supplier_id, supplier_name)
        
        with transaction.atomic():
            movement = MovementInventory.objects.create(
                variant=variant,
                quantity=quantity,
                movement_type=MovementInventory.MovementType.PURCHASE,
                observation=f"Compra - Proveedor: {supplier_name}" if supplier_name else "Compra directa",
                supplier=supplier,
                created_by=user.username if user else "system",
            )
            
            if supplier:
                supplier.last_purchase_date = now().date()
                supplier.save()
            
            cls._log_movement("create_purchase", movement, {
                "variant_id": variant_id,
                "quantity": quantity,
                "unit_cost": float(unit_cost),
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "product_name": variant.product.name,
            }, user)
            
            return movement
    
    @classmethod
    def create_adjustment(cls, variant_id: int, quantity: int, reason: str, user=None) -> MovementInventory:
        """Crear ajuste de inventario (corrección manual)"""
        if not reason or not reason.strip():
            raise ValidationError("El motivo del ajuste es requerido")
        
        variant = cls._validate_variant_exists(variant_id)
        
        with transaction.atomic():
            movement = MovementInventory.objects.create(
                variant=variant,
                quantity=quantity,
                movement_type=MovementInventory.MovementType.ADJUSTMENT,
                observation=f"Ajuste: {reason}",
                created_by=user.username if user else "system",
            )
            
            cls._log_movement("create_adjustment", movement, {
                "variant_id": variant_id,
                "quantity": quantity,
                "reason": reason,
                "product_name": variant.product.name,
            }, user)
            
            return movement
    
    @classmethod
    def create_sale_return(cls, sale_id: int, items: list, reason: str, user=None) -> list:
        """Crear devolución de venta (entrada de inventario)"""
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
                
                try:
                    detail = SaleDetail.objects.get(id=sale_detail_id, sale=sale)
                except SaleDetail.DoesNotExist:
                    raise ValidationError(f"El detalle de venta {sale_detail_id} no existe")
                
                if quantity <= 0:
                    raise ValidationError("La cantidad a devolver debe ser mayor a cero")
                
                if quantity > detail.quantity:
                    raise ValidationError(f"No se pueden devolver más de {detail.quantity} unidades")
                
                movement = MovementInventory.objects.create(
                    variant=detail.variant,
                    quantity=quantity,
                    movement_type=MovementInventory.MovementType.SALE_RETURN,
                    sale=sale,
                    observation=f"Devolución venta #{sale.id} - {reason}",
                    created_by=user.username if user else "system",
                )
                
                movements_created.append(movement)
                
                cls._log_movement("create_sale_return", movement, {
                    "sale_id": sale_id,
                    "sale_detail_id": sale_detail_id,
                    "quantity": quantity,
                    "reason": reason,
                    "product_name": detail.variant.product.name,
                }, user)
        
        return movements_created
    
    @classmethod
    def create_supplier_return(cls, variant_id: int, quantity: int, reason: str, 
                             supplier_id: int = None, supplier_name: str = "", user=None) -> MovementInventory:
        """Crear devolución a proveedor (salida de inventario)"""
        if quantity <= 0:
            raise ValidationError("La cantidad a devolver debe ser mayor a cero")
        
        if not reason or not reason.strip():
            raise ValidationError("El motivo de la devolución es requerido")
        
        variant = cls._validate_variant_exists(variant_id)
        supplier, supplier_name = cls._get_supplier(supplier_id, supplier_name)
        
        current_stock = variant.stock
        if current_stock < quantity:
            raise ValidationError(f"Stock insuficiente. Actual: {current_stock}, Requerido: {quantity}")
        
        with transaction.atomic():
            movement = MovementInventory.objects.create(
                variant=variant,
                quantity=-quantity,
                movement_type=MovementInventory.MovementType.RETURN,
                observation=f"Devolución proveedor {supplier_name} - {reason}" if supplier_name else f"Devolución proveedor - {reason}",
                supplier=supplier,
                created_by=user.username if user else "system",
            )
            
            cls._log_movement("create_supplier_return", movement, {
                "variant_id": variant_id,
                "quantity": quantity,
                "reason": reason,
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "product_name": variant.product.name,
                "current_stock": current_stock,
            }, user)
            
            return movement


class InventoryService:
    """Servicios para gestión de inventario"""
    
    @staticmethod
    def _validate_month_closure(year: int, month: int) -> date:
        """Valida que el mes puede ser cerrado y retorna la fecha del mes"""
        month_date = date(year, month, 1)
        today = date.today().replace(day=1)
        
        if month_date > today:
            raise ValidationError("No se puede cerrar un mes futuro")
        
        if InventorySnapshot.objects.filter(month=month_date).exists():
            raise ValidationError("Este mes ya fue cerrado")
        
        return month_date
    
    @staticmethod
    def _calculate_variant_month_balance(variant: ProductVariant, year: int, month: int) -> dict:
        """Calcula el balance de una variante para un mes específico"""
        month_date = date(year, month, 1)
        
        prev_snapshot = (
            InventorySnapshot.objects
            .filter(variant=variant, month__lt=month_date)
            .order_by("-month")
            .first()
        )
        
        stock_opening = prev_snapshot.stock_closing if prev_snapshot else 0
        
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
        
        return {
            "stock_opening": stock_opening,
            "total_in": total_in,
            "total_out": total_out,
            "stock_closing": stock_closing,
        }
    
    @staticmethod
    def _create_month_snapshot(variant: ProductVariant, month_date: date, balance_data: dict) -> InventorySnapshot:
        """Crea el snapshot mensual para una variante"""
        return InventorySnapshot.objects.create(
            month=month_date,
            variant=variant,
            stock_opening=balance_data["stock_opening"],
            total_in=balance_data["total_in"],
            total_out=balance_data["total_out"],
            stock_closing=balance_data["stock_closing"],
        )
    
    @staticmethod
    def _log_month_closure(year: int, month: int) -> None:
        """Registra en auditoría el cierre de mes"""
        AuditLog.objects.create(
            action="close_inventory_month",
            entity="inventory",
            entity_id=0,
            performed_by="system",
            extra_data={
                "year": year,
                "month": month,
            },
        )
    
    @classmethod
    def close_inventory_month(cls, year: int, month: int) -> None:
        """Genera el snapshot de inventario para un mes específico"""
        month_date = cls._validate_month_closure(year, month)
        
        with transaction.atomic():
            for variant in ProductVariant.objects.all():
                balance_data = cls._calculate_variant_month_balance(variant, year, month)
                cls._create_month_snapshot(variant, month_date, balance_data)
            
            cls._log_month_closure(year, month)


# Función de compatibilidad - mantener la interfaz original
def close_inventory_month(year: int, month: int) -> None:
    """Función de compatibilidad para close_inventory_month"""
    return InventoryService.close_inventory_month(year, month)


# Función de compatibilidad - mantener la interfaz original
def create_purchase(variant_id: int, quantity: int, unit_cost: float, supplier_id: int = None, supplier_name: str = "", user=None) -> MovementInventory:
    """Función de compatibilidad para create_purchase"""
    return MovementService.create_purchase(variant_id, quantity, unit_cost, supplier_id, supplier_name, user)


# Función de compatibilidad - mantener la interfaz original
def create_adjustment(variant_id: int, quantity: int, reason: str, user=None) -> MovementInventory:
    """Función de compatibilidad para create_adjustment"""
    return MovementService.create_adjustment(variant_id, quantity, reason, user)


# Función de compatibilidad - mantener la interfaz original
def create_sale_return(sale_id: int, items: list, reason: str, user=None) -> list:
    """Función de compatibilidad para create_sale_return"""
    return MovementService.create_sale_return(sale_id, items, reason, user)


# Función de compatibilidad - mantener la interfaz original
def create_supplier_return(variant_id: int, quantity: int, reason: str, supplier_id: int = None, supplier_name: str = "", user=None) -> MovementInventory:
    """Función de compatibilidad para create_supplier_return"""
    return MovementService.create_supplier_return(variant_id, quantity, reason, supplier_id, supplier_name, user)


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

    @classmethod
    def optimize_image(cls, image_file):
        """
        Optimiza la imagen: redimensiona a dimensiones máximas y comprime
        
        Args:
            image_file: Archivo de imagen a optimizar (modifica en lugar)
        """
        try:
            img = Image.open(image_file)
            
            # Redimensionar si supera las dimensiones máximas
            if img.width > cls.MAX_DIMENSIONS[0] or img.height > cls.MAX_DIMENSIONS[1]:
                img.thumbnail(cls.MAX_DIMENSIONS, Image.LANCZOS)
            
            # Comprimir: convertir a JPEG con calidad 85 para ahorrar espacio sin perder mucha calidad
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Guardar con compresión
            output = BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            # Reemplazar el archivo original con la versión optimizada
            with open(image_file.path, 'wb') as f:
                f.write(output.getvalue())
                
        except Exception as e:
            # No fallar si la optimización falla, solo loggear
            print(f"Error optimizando imagen: {e}")