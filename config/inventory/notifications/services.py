import os
import logging
from django.core.mail import send_mail
from django.conf import settings
import urllib.request
import json

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def send_new_sale_alert(sale):
        """
        Envía alertas de nueva venta por Email y WhatsApp
        """
        if not getattr(settings, 'NOTIFICATIONS_ENABLED', True):
            return

        manager_phone = getattr(settings, 'NOTIFICATIONS_MANAGER_PHONE', '')
        manager_email = getattr(settings, 'NOTIFICATIONS_MANAGER_EMAIL', '')
        
        # 1. Preparar el mensaje
        customer_name = sale.customer_name if hasattr(sale, 'customer_name') else 'Cliente'
        total = f"${sale.total:,.0f}"
        items_count = sale.details.count()
        
        message = (
            f"🛍️ *Nueva Venta en Golos Store*\n\n"
            f"👤 *Cliente:* {customer_name}\n"
            f"💰 *Total:* {total}\n"
            f"📦 *Productos:* {items_count}\n"
            f"📅 *Fecha:* {sale.created_at.strftime('%d/%m/%Y %H:%M')}\n\n"
            f"Ver detalles en el panel: {getattr(settings, 'STORE_FRONTEND_URL', '')}/sales"
        )

        # 2. Enviar por WhatsApp (Placeholder logic/Whapi/Twilio)
        if manager_phone:
            NotificationService._send_whatsapp(manager_phone, message)
            
        # 3. Enviar por Email
        if manager_email:
            NotificationService._send_email(
                subject=f"Nueva Venta registrada: {total}",
                message=message.replace('*', ''), # Quitar negritas MD para email plano
                recipient=manager_email
            )

    @staticmethod
    def _send_whatsapp(phone, message):
        """
        Envía mensaje por WhatsApp usando integración externa (ej: Whapi)
        """
        api_url = getattr(settings, 'NOTIFICATIONS_WHATSAPP_URL', '')
        api_token = getattr(settings, 'NOTIFICATIONS_WHATSAPP_TOKEN', '')
        
        if not api_url or not api_token:
            logger.info(f"[NOTIF] WhatsApp (Simulado) a {phone}: {message}")
            return

        try:
            data = json.dumps({
                "to": phone,
                "body": message
            }).encode('utf-8')
            
            req = urllib.request.Request(
                api_url, 
                data=data, 
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_token}'
                }
            )
            
            with urllib.request.urlopen(req) as f:
                logger.info(f"WhatsApp enviado exitosamente a {phone}")
        except Exception as e:
            logger.error(f"Error enviando WhatsApp: {str(e)}")

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
