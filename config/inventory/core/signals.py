from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import Sum
from ..models import SaleDetail, Sale, MovementInventory
from ..notifications.services import NotificationService
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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

@receiver(pre_save, sender=Sale)
def capture_old_status(sender, instance, **kwargs):
    """Captura el estado anterior de la venta para detectar cambios"""
    if instance.pk:
        try:
            old_instance = Sale.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Sale.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Sale)
def notify_manager_on_new_sale(sender, instance, created, **kwargs):
    """
    Envía una notificación al administrador cuando se confirma una venta
    """
    old_status = getattr(instance, '_old_status', None)
    
    # Consideramos "confirmada" si el status pasa a paid, processing o completed
    is_confirmed_now = instance.status in ['paid', 'processing', 'completed']
    was_confirmed_before = old_status in ['paid', 'processing', 'completed']

    should_notify = False
    if created and is_confirmed_now:
        should_notify = True
    elif not created and is_confirmed_now and not was_confirmed_before:
        should_notify = True

    if should_notify:
        try:
            NotificationService.send_new_sale_alert(instance)
        except Exception:
            # No bloqueamos el flujo de la venta si falla la notificación
            pass

def broadcast_stock_update(variant):
    """Envía la actualización de stock por WebSockets"""
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            'stock_updates',
            {
                'type': 'stock_update',
                'variant_id': variant.id,
                'new_stock': variant.stock
            }
        )

@receiver(post_save, sender=MovementInventory)
def stock_movement_saved(sender, instance, **kwargs):
    broadcast_stock_update(instance.variant)

@receiver(post_delete, sender=MovementInventory)
def stock_movement_deleted(sender, instance, **kwargs):
    broadcast_stock_update(instance.variant)