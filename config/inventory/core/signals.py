from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from ..models import SaleDetail, Sale
from ..notifications.services import NotificationService

@receiver(post_save, sender=SaleDetail)
def update_sale_total_on_save(sender, instance, **kwargs):
    """Se ejecuta después de crear o editar un detalle"""
    sale = instance.sale
    # Calculamos la suma de todos los subtotales
    total_sum = sale.details.aggregate(total=Sum('subtotal'))['total'] or 0
    sale.total = total_sum
    sale.save(update_fields=['total'])

@receiver(post_delete, sender=SaleDetail)
def update_sale_total_on_delete(sender, instance, **kwargs):
    """Se ejecuta después de eliminar un detalle"""
    sale = instance.sale
    total_sum = sale.details.aggregate(total=Sum('subtotal'))['total'] or 0
    sale.total = total_sum
    sale.save(update_fields=['total'])

@receiver(post_save, sender=Sale)
def notify_manager_on_new_sale(sender, instance, created, **kwargs):
    """
    Envía una notificación al administrador cuando se crea una nueva venta
    """
    if created:
        try:
            NotificationService.send_new_sale_alert(instance)
        except Exception:
            # No bloqueamos el flujo de la venta si falla la notificación
            pass