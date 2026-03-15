import requests
import os
import logging
from django.conf import settings
from django.utils.timezone import now
from ..models import Sale, ElectronicInvoice

logger = logging.getLogger(__name__)

class FactusService:
    """
    Servicio para la integración con Factus (Facturación Electrónica en Colombia).
    """
    
    BASE_URL = os.getenv('FACTUS_API_URL', 'https://api-sandbox.factus.com.co/v1')
    EMAIL = os.getenv('FACTUS_EMAIL')
    PASSWORD = os.getenv('FACTUS_PASSWORD')
    
    @classmethod
    def _get_auth_token(cls):
        """
        Obtiene el token de autenticación (Bearer Token) de Factus.
        En una implementación real, esto debería estar cacheado.
        """
        url = f"{cls.BASE_URL}/auth/login"
        payload = {
            "email": cls.EMAIL,
            "password": cls.PASSWORD
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('access_token')
        except Exception as e:
            logger.error(f"Error autenticando con Factus: {str(e)}")
            return None

    @classmethod
    def create_invoice(cls, sale: Sale):
        """
        Envía una venta a Factus para generar la factura electrónica.
        """
        token = cls._get_auth_token()
        if not token:
            return None, "Error de autenticación con el proveedor"

        # 1. Preparar el payload (Simplificado para la estructura base)
        # En una implementación real, aquí transformamos el Sale y SaleDetail 
        # al formato específico solicitado por Factus.
        payload = cls._prepare_invoice_payload(sale)
        
        url = f"{cls.BASE_URL}/bills"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            data = response.json()
            
            if response.status_code == 201:
                # Éxito: Crear registro en nuestra DB
                invoice_data = data.get('data', {})
                return cls._persist_invoice(sale, invoice_data), None
            else:
                error_msg = data.get('message', 'Error desconocido en Factus')
                logger.error(f"Error Factus (Sale {sale.id}): {error_msg}")
                return None, error_msg
                
        except Exception as e:
            logger.error(f"Excepción comunicando con Factus: {str(e)}")
            return None, str(e)

    @staticmethod
    def _prepare_invoice_payload(sale: Sale):
        """
        Transforma nuestro modelo Sale al formato JSON de Factus.
        """
        # Nota: Este es un ejemplo conceptual. Factus requiere NIT, Nombres, 
        # Detalles con IVA, etc.
        details = []
        for item in sale.details.all():
            details.append({
                "code": f"PROD-{item.variant.id}",
                "name": item.variant.product.name,
                "quantity": item.quantity,
                "price": float(item.price),
                "tax_rate": "19.00", # Ejemplo IVA 19%
                "discount": 0
            })
            
        return {
            "numbering_range_id": os.getenv('FACTUS_NUMBERING_ID'),
            "reference_code": f"GOLOS-{sale.id}",
            "customer": {
                "identification": "222222222222", # Consumidor Final por defecto
                "names": sale.customer,
                "email": "correo@cliente.com" # Importante para factura electrónica
            },
            "items": details,
            "payment_method_code": "1", # Efectivo
            "is_post": False
        }

    @staticmethod
    def _persist_invoice(sale, data):
        """
        Guarda los datos legales retornados por Factus en nuestro modelo.
        """
        invoice, created = ElectronicInvoice.objects.update_or_create(
            sale=sale,
            defaults={
                "external_id": data.get('id'),
                "number": data.get('number'),
                "cufe": data.get('cufe'),
                "qr_data": data.get('qr_data'),
                "pdf_url": data.get('pdf_url'),
                "xml_url": data.get('xml_url'),
                "status": 'accepted',
                "dian_response_at": now()
            }
        )
        
        # Actualizar la venta
        sale.is_electronic_invoice = True
        sale.document_number = data.get('number')
        sale.save()
        
        return invoice
