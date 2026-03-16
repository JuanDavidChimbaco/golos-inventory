from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from ..notifications.services import NotificationService

@receiver(user_logged_in)
def notify_user_on_login(sender, request, user, **kwargs):
    """
    Envía una notificación al usuario cuando inicia sesión
    """
    try:
        NotificationService.send_login_notification(user, request)
    except Exception:
        # No bloqueamos el login si falla la notificación
        pass
