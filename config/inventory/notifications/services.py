import os
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import urllib.request
import json

logger = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from ..models import SystemNotification
import urllib.parse

class NotificationService:
    @staticmethod
    def send_new_sale_alert(sale):
        """
        Envía alertas de nueva venta por Email y WhatsApp,
        y crea las notificaciones del sistema de la gestión.
        """
        if not getattr(settings, 'NOTIFICATIONS_ENABLED', True):
            return

        manager_email = getattr(settings, 'NOTIFICATIONS_MANAGER_EMAIL', '')
        
        # 1. Preparar el mensaje
        customer_name = getattr(sale, 'customer', 'Cliente')
        total = f"${sale.total:,.0f}"
        items_count = sale.details.count()
        
        message = (
            f"🛍️ *Nueva Venta en Golos Store*\n\n"
            f"👤 *Cliente:* {customer_name}\n"
            f"💰 *Total:* {total}\n"
            f"📦 *Productos:* {items_count}\n"
            f"📅 *Fecha:* {sale.created_at.strftime('%d/%m/%Y %H:%M')}"
        )

        # 2. Crear Alertas para los Administradores (Campanita DB)
        User = get_user_model()
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            SystemNotification.objects.create(
                user=admin,
                title="Nueva Venta en Tienda",
                message=f"{customer_name} compró {items_count} producto(s) por {total}.",
                type="sale",
                related_link="/sales"
            )

        # 3. Notificar al Frontend por WebSocket (para que aparezca el punto rojo instantáneamente)
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                'stock_updates', # Interceptamos el mismo websocket para ahorrar conexiones
                {
                    'type': 'system_alert',
                    'message': 'Nueva Venta'
                }
            )

        # 4. Enviar Alerta por Telegram (Grupo oficial de la tienda)
        NotificationService._send_telegram(message)
            
        # 5. Enviar por Email (si está configurado)
        if manager_email:
            NotificationService._send_email(
                subject=f"Nueva Venta registrada: {total}",
                message=message.replace('*', ''), 
                recipient=manager_email
            )

    @staticmethod
    def send_login_notification(user, request):
        """
        Envía una alerta de inicio de sesión al usuario
        """
        if not getattr(settings, 'NOTIFICATIONS_ENABLED', True):
            return

        user_email = user.email
        if not user_email:
            return

        # Capturar info del dispositivo/IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT', 'Desconocido')
        date_str = timezone.now().strftime('%d/%m/%Y %H:%M')

        subject = "🛡️ Alerta de Inicio de Sesión - Golos Store"
        message = (
            f"Hola {user.first_name or user.username},\n\n"
            f"Se ha detectado un nuevo inicio de sesión en tu cuenta de Golos Store.\n\n"
            f"📅 Fecha: {date_str}\n"
            f"🌐 Dirección IP: {ip}\n"
            f"💻 Dispositivo: {user_agent}\n\n"
            f"Si fuiste tú, puedes ignorar este correo. "
            f"Si no reconoces esta actividad, por favor cambia tu contraseña inmediatamente."
        )

        NotificationService._send_email(
            subject=subject,
            message=message,
            recipient=user_email
        )

    @staticmethod
    def _send_telegram(message):
        """
        Envía mensaje a un Chat o Grupo de Telegram
        """
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '')
        
        if not bot_token or not chat_id:
            logger.warning("No hay TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID configurado en el .env")
            return

        try:
            encoded_message = urllib.parse.quote(message)
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={encoded_message}&parse_mode=Markdown"
            
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req) as response:
                if response.getcode() == 200:
                    logger.info("Alerta de venta enviada exitosamente por Telegram.")
                else:
                    logger.error(f"Fallo enviando alerta de Telegram: {response.getcode()}")
        except Exception as e:
            logger.error(f"Error enviando notificación vía Telegram: {str(e)}")

    @staticmethod
    def _send_email(subject, message, recipient):
        """
        Envía email usando el backend configurado en Django
        """
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@golosshoes.shop'),
                recipient_list=[recipient],
                fail_silently=False,
            )
            logger.info(f"Email de notificación enviado a {recipient}")
        except Exception as e:
            logger.error(f"Error enviando Email: {str(e)}")
