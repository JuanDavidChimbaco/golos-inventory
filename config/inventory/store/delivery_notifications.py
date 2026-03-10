"""
Vistas adicionales para notificaciones de entrega económicas.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from ..core.api_responses import error_response, success_response
from ..models import AuditLog, Sale, Shipment

logger = logging.getLogger(__name__)


def _generate_delivery_confirmation_token(sale: Sale) -> str:
    """
    Genera un token seguro para confirmación de entrega.
    """
    data = f"{sale.id}:{sale.payment_reference}:{sale.created_at.isoformat()}"
    hash_obj = hashlib.sha256(data.encode("utf-8"))
    return hash_obj.hexdigest()[:32]


def _can_confirm_delivery(sale: Sale, source: str = "customer") -> tuple[bool, str]:
    """
    Validaciones avanzadas para confirmación de entrega.
    """
    # 1. Estado válido
    if sale.status in {"completed", "canceled"}:
        return False, "Orden ya completada o cancelada"
    
    # 2. Tiempo mínimo en tránsito (evitar confirmaciones prematuras)
    if sale.shipped_at:
        min_hours = int(getattr(settings, "STORE_DELIVERY_MIN_TRANSIT_HOURS", "2"))
        if timezone.now() < sale.shipped_at + timedelta(hours=min_hours):
            return False, f"Debe esperar al menos {min_hours} horas después del envío"
    
    # 3. Tiempo máximo en tránsito (evitar estancados)
    if sale.shipped_at:
        max_hours = int(getattr(settings, "STORE_DELIVERY_MAX_TRANSIT_HOURS", "168"))  # 7 días
        if timezone.now() > sale.shipped_at + timedelta(hours=max_hours):
            return False, f"Tiempo máximo de tránsito excedido ({max_hours} horas)"
    
    # 4. Validaciones específicas por fuente
    if source == "customer":
        # El cliente puede confirmar, pero se marcará como "pendiente de verificación"
        return True, "customer_confirmation"
    elif source == "webhook":
        # Webhook de transportadora es confiable
        return True, "webhook_confirmed"
    elif source == "staff":
        # Staff puede confirmar manualmente
        return True, "staff_verified"
    
    return False, "Fuente no válida"


def _create_delivery_verification_request(sale: Sale, confirmed_by: str) -> dict:
    """
    Crea una solicitud de verificación cuando el cliente confirma.
    """
    verification_data = {
        "sale_id": sale.id,
        "confirmed_by": confirmed_by,
        "confirmed_at": timezone.now().isoformat(),
        "verification_status": "pending",
        "requires_photo": True,
        "requires_id": False,
        "verification_methods": ["photo_proof", "gps_location", "signature"],
    }
    
    AuditLog.objects.create(
        action="store_delivery_verification_requested",
        entity="sale",
        entity_id=sale.id,
        performed_by=confirmed_by,
        extra_data=verification_data,
    )
    
    return verification_data


@extend_schema(tags=["Store"])
class StoreDeliveryConfirmationView(APIView):
    """
    Vista pública para que los clientes confirmen recepción de pedidos.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, sale_id: int, token: str):
        """
        Muestra página de confirmación de entrega.
        """
        sale = get_object_or_404(Sale, id=sale_id, is_order=True)
        
        # Validar token
        expected_token = _generate_delivery_confirmation_token(sale)
        if token != expected_token:
            return error_response(
                detail="Token de confirmación inválido",
                code="STORE_DELIVERY_CONFIRMATION_INVALID_TOKEN",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        if sale.status in {"completed", "canceled"}:
            return error_response(
                detail="Este pedido ya fue completado o cancelado",
                code="STORE_DELIVERY_CONFIRMATION_NOT_ALLOWED",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        return success_response(
            detail="Página de confirmación de entrega",
            code="STORE_DELIVERY_CONFIRMATION_PAGE",
            order={
                "sale_id": sale.id,
                "customer": sale.customer,
                "total": str(sale.total),
                "created_at": sale.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "current_status": sale.status,
            },
        )

    def post(self, request, sale_id: int, token: str):
        """
        Procesa la confirmación de entrega del cliente con verificación.
        """
        sale = get_object_or_404(Sale, id=sale_id, is_order=True)
        
        # Validar token
        expected_token = _generate_delivery_confirmation_token(sale)
        if token != expected_token:
            return error_response(
                detail="Token de confirmación inválido",
                code="STORE_DELIVERY_CONFIRMATION_INVALID_TOKEN",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Validar si puede confirmar
        can_confirm, reason = _can_confirm_delivery(sale, "customer")
        if not can_confirm:
            return error_response(
                detail=reason,
                code="STORE_DELIVERY_CONFIRMATION_NOT_ALLOWED",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        with transaction.atomic():
            # NO marcar como delivered directamente
            # En su lugar, crear solicitud de verificación
            verification_data = _create_delivery_verification_request(sale, "customer")
            
            # Cambiar estado a "pending_verification" en lugar de "delivered"
            old_status = sale.status
            sale.status = "pending_verification"
            sale.save(update_fields=["status", "updated_at"])
            
            # Actualizar envío si existe
            shipment = sale.shipments.first()
            if shipment:
                shipment.status = "pending_verification"
                shipment.save(update_fields=["status", "updated_at"])
            
            # Registrar auditoría
            AuditLog.objects.create(
                action="store_order_delivery_confirmed_by_customer_pending_verification",
                entity="sale",
                entity_id=sale.id,
                performed_by="customer_confirmation",
                extra_data={
                    "old_status": old_status,
                    "new_status": "pending_verification",
                    "confirmed_at": timezone.now().isoformat(),
                    "verification_data": verification_data,
                },
            )
        
        return success_response(
            detail="¡Gracias! Tu confirmación ha sido recibida. Está pendiente de verificación por nuestro equipo.",
            code="STORE_DELIVERY_CONFIRMATION_PENDING_VERIFICATION",
            order_id=sale.id,
            order_status=sale.status,
            next_steps=[
                "Nuestro equipo verificará la entrega",
                "Puedes ser contactado para confirmación adicional",
                "Recibirás notificación cuando se complete la verificación",
            ],
        )


@extend_schema(tags=["StoreOps"])
class StoreOpsDeliveryNotificationView(APIView):
    """
    Envía notificación de entrega al cliente (email/SMS).
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, sale_id: int):
        """
        Envía notificación con enlace de confirmación al cliente.
        """
        if not request.user.has_perm("inventory.change_sale"):
            return error_response(
                detail="No tienes permisos para enviar notificaciones",
                code="PERMISSION_DENIED",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        
        sale = get_object_or_404(Sale, id=sale_id, is_order=True)
        
        if sale.status not in {"shipped", "processing"}:
            return error_response(
                detail="Solo se pueden notificar pedidos enviados o en proceso",
                code="STORE_DELIVERY_NOTIFICATION_INVALID_STATUS",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Generar token y enlace de confirmación
        token = _generate_delivery_confirmation_token(sale)
        base_url = getattr(settings, "STORE_FRONTEND_URL", "http://localhost:3000")
        confirmation_link = f"{base_url}/store/delivery-confirmation/{sale.id}/{token}"
        
        # Obtener información del cliente
        customer_info = sale.shipping_address or {}
        customer_email = customer_info.get("email")
        customer_phone = customer_info.get("phone")
        
        notification_methods = []
        
        # TODO: Integrar servicio de email (puede ser Django mail backend)
        if customer_email:
            # Aquí se enviaría el email
            notification_methods.append("email")
            logger.info(f"Email de confirmación enviado para orden {sale.id} a {customer_email}")
        
        # TODO: Integrar servicio SMS (Twilio, MessageBird, etc.)
        if customer_phone:
            # Aquí se enviaría el SMS
            notification_methods.append("sms")
            logger.info(f"SMS de confirmación enviado para orden {sale.id} a {customer_phone}")
        
        # Registrar auditoría
        AuditLog.objects.create(
            action="store_delivery_notification_sent",
            entity="sale",
            entity_id=sale.id,
            performed_by=request.user.username,
            extra_data={
                "notification_methods": notification_methods,
                "confirmation_link": confirmation_link,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
            },
        )
        
        return success_response(
            detail="Notificación de entrega enviada exitosamente",
            code="STORE_DELIVERY_NOTIFICATION_SENT",
            order_id=sale.id,
            notification_methods=notification_methods,
            confirmation_link=confirmation_link,
        )


@extend_schema(tags=["StoreOps"])
class StoreOpsDeliveryVerificationView(APIView):
    """
    Vista para que el staff verifique las entregas confirmadas por clientes.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, sale_id: int):
        """
        Obtiene información de verificación para una orden.
        """
        if not request.user.has_perm("inventory.change_sale"):
            return error_response(
                detail="No tienes permisos para verificar entregas",
                code="PERMISSION_DENIED",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        
        sale = get_object_or_404(Sale, id=sale_id, is_order=True)
        
        # Buscar solicitudes de verificación
        verification_logs = AuditLog.objects.filter(
            entity="sale",
            entity_id=sale.id,
            action__in=[
                "store_delivery_verification_requested",
                "store_order_delivery_confirmed_by_customer_pending_verification",
            ]
        ).order_by("-created_at")
        
        verification_data = []
        for log in verification_logs:
            verification_data.append({
                "requested_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "confirmed_by": log.performed_by,
                "verification_status": log.extra_data.get("verification_status", "unknown"),
                "requires_photo": log.extra_data.get("requires_photo", False),
                "requires_id": log.extra_data.get("requires_id", False),
                "verification_methods": log.extra_data.get("verification_methods", []),
            })
        
        return success_response(
            detail="Información de verificación obtenida",
            code="STORE_DELIVERY_VERIFICATION_INFO",
            order={
                "sale_id": sale.id,
                "customer": sale.customer,
                "status": sale.status,
                "shipped_at": sale.shipped_at.strftime("%Y-%m-%d %H:%M:%S") if sale.shipped_at else None,
            },
            verification_data=verification_data,
        )
    
    def post(self, request, sale_id: int):
        """
        Procesa la verificación de entrega por parte del staff.
        """
        if not request.user.has_perm("inventory.change_sale"):
            return error_response(
                detail="No tienes permisos para verificar entregas",
                code="PERMISSION_DENIED",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        
        sale = get_object_or_404(Sale, id=sale_id, is_order=True)
        
        if sale.status != "pending_verification":
            return error_response(
                detail="Esta orden no está pendiente de verificación",
                code="STORE_DELIVERY_VERIFICATION_NOT_PENDING",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        
        verification_method = request.data.get("verification_method", "staff_manual")
        verification_notes = request.data.get("notes", "")
        verified = request.data.get("verified", False)
        
        with transaction.atomic():
            if verified:
                # Marcar como delivered
                now = timezone.now()
                old_status = sale.status
                sale.status = "delivered"
                sale.delivered_at = now
                sale.save(update_fields=["status", "delivered_at", "updated_at"])
                
                # Actualizar envío
                shipment = sale.shipments.first()
                if shipment:
                    shipment.status = Shipment.ShipmentStatus.DELIVERED
                    shipment.save(update_fields=["status", "updated_at"])
                
                # Registrar auditoría
                AuditLog.objects.create(
                    action="store_order_delivery_verified_by_staff",
                    entity="sale",
                    entity_id=sale.id,
                    performed_by=request.user.username,
                    extra_data={
                        "old_status": old_status,
                        "new_status": "delivered",
                        "verified_at": now.isoformat(),
                        "verification_method": verification_method,
                        "verification_notes": verification_notes,
                    },
                )
                
                return success_response(
                    detail="Entrega verificada y marcada como completada",
                    code="STORE_DELIVERY_VERIFICATION_SUCCESS",
                    order_id=sale.id,
                    order_status=sale.status,
                )
            else:
                # Rechazar verificación
                sale.status = "shipped"  # Volver a shipped
                sale.save(update_fields=["status", "updated_at"])
                
                # Registrar auditoría
                AuditLog.objects.create(
                    action="store_order_delivery_verification_rejected",
                    entity="sale",
                    entity_id=sale.id,
                    performed_by=request.user.username,
                    extra_data={
                        "old_status": "pending_verification",
                        "new_status": "shipped",
                        "rejection_reason": verification_notes,
                        "verification_method": verification_method,
                    },
                )
                
                return success_response(
                    detail="Verificación rechazada. Orden devuelta a estado 'shipped'",
                    code="STORE_DELIVERY_VERIFICATION_REJECTED",
                    order_id=sale.id,
                    order_status=sale.status,
                )


@extend_schema(tags=["Store"])
class StoreDeliveryTrackingPublicView(APIView):
    """
    Vista pública para seguimiento de envíos (sin autenticación).
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, tracking_number: str):
        """
    Permite a cualquiera consultar el estado de un envío por número de guía.
    """
        shipment = Shipment.objects.filter(
            tracking_number__iexact=tracking_number.strip().upper()
        ).select_related("sale").first()
        
        if not shipment:
            return error_response(
                detail="Número de guía no encontrado",
                code="STORE_TRACKING_NOT_FOUND",
                http_status=status.HTTP_404_NOT_FOUND,
            )
        
        sale = shipment.sale
        
        # Generar token de confirmación si está entregado o en camino
        confirmation_token = None
        confirmation_link = None
        if shipment.status in {Shipment.ShipmentStatus.IN_TRANSIT, Shipment.ShipmentStatus.CREATED}:
            confirmation_token = _generate_delivery_confirmation_token(sale)
            base_url = getattr(settings, "STORE_FRONTEND_URL", "http://localhost:3000")
            confirmation_link = f"{base_url}/store/delivery-confirmation/{sale.id}/{confirmation_token}"
        
        return success_response(
            detail="Información de seguimiento obtenida",
            code="STORE_TRACKING_INFO_OK",
            shipment={
                "carrier": shipment.carrier,
                "tracking_number": shipment.tracking_number,
                "status": shipment.status,
                "service": shipment.service,
                "shipping_cost": str(shipment.shipping_cost),
                "created_at": shipment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "label_url": shipment.label_url,
            },
            order={
                "sale_id": sale.id,
                "customer": sale.customer,
                "total": str(sale.total),
                "status": sale.status,
                "created_at": sale.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            },
            confirmation_link=confirmation_link,
        )
