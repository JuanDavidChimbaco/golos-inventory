from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.core.files import File
from PIL import Image
from io import BytesIO
from .models import MovementInventory, Sale, ProductImage


def confirm_sale(sale_id: int, user) -> None:
    with transaction.atomic():
        # Traer la venta con bloqueo para evitar concurrentes
        sale = Sale.objects.select_for_update().get(id=sale_id)

        # Validaciones basicas
        if sale.status != "pending":
            raise ValidationError("La venta no está pendiente")

        details = sale.details.select_related("variant").all()
        if not details:
            raise ValidationError("La venta no tiene Productos")

        # validar stock por variante
        for detail in details:
            stock = (
                detail.variant.movements.aggregate(total=Sum("quantity"))["total"] or 0
            )
            if stock < detail.quantity:
                raise ValidationError(
                    f"Stock insuficiente para el producto {detail.variant.product.name}"
                )

        # confirmar venta
        sale.status = "completed"
        sale.created_by = user.username
        sale.save()

        # crear movimientos
        movements = []
        for detail in details:
            movements.append(
                MovementInventory(
                    variant=detail.variant,
                    movement_type="sale",
                    quantity=-detail.quantity,
                    created_by=user.username,
                )
            )
        MovementInventory.objects.bulk_create(movements)


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
