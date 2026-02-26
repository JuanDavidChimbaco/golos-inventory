"""
Integracion base de transportadora para ordenes de tienda.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import hmac
import json
from typing import Any
from urllib import error, request
from uuid import uuid4

from django.conf import settings

from ..models import Sale, Shipment


class ShippingProviderError(Exception):
    pass


@dataclass(frozen=True)
class ShippingServiceOption:
    name: str
    cost: Decimal
    eta_hours: int


def _provider_mode() -> str:
    return str(getattr(settings, "STORE_SHIPPING_PROVIDER", "mock")).strip().lower() or "mock"


def _shipping_services() -> list[ShippingServiceOption]:
    # Formato: "eco:12000:72,standard:18000:48,express:25000:24"
    raw = getattr(settings, "STORE_SHIPPING_SERVICES", "eco:12000:72,standard:18000:48,express:25000:24")
    options: list[ShippingServiceOption] = []
    for chunk in str(raw).split(","):
        item = chunk.strip()
        if not item:
            continue
        try:
            name, cost, eta = item.split(":")
            options.append(
                ShippingServiceOption(
                    name=name.strip(),
                    cost=Decimal(cost.strip()),
                    eta_hours=int(eta.strip()),
                )
            )
        except (ValueError, ArithmeticError):
            continue

    if not options:
        options = [ShippingServiceOption(name="eco", cost=Decimal("12000"), eta_hours=72)]
    return options


def choose_best_service() -> ShippingServiceOption:
    max_eta = int(getattr(settings, "STORE_SHIPPING_MAX_DELIVERY_HOURS", 72))
    options = _shipping_services()
    valid = [option for option in options if option.eta_hours <= max_eta]
    target = valid or options
    return sorted(target, key=lambda option: (option.cost, option.eta_hours))[0]


def _http_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    data = None
    final_headers = {"Content-Type": "application/json"}
    final_headers.update(headers or {})
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, data=data, headers=final_headers, method=method.upper())
    timeout_seconds = int(getattr(settings, "STORE_SHIPPING_API_TIMEOUT_SECONDS", 15))
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8") or "{}"
            return json.loads(body)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise ShippingProviderError(f"HTTP {exc.code}: {detail}")
    except Exception as exc:
        raise ShippingProviderError(str(exc))


def _sale_payload_for_provider(sale: Sale, service: ShippingServiceOption) -> dict[str, Any]:
    details = sale.details.select_related("variant__product").all()
    items = [
        {
            "variant_id": detail.variant_id,
            "product": detail.variant.product.name,
            "quantity": int(detail.quantity),
            "unit_price": str(detail.price),
        }
        for detail in details
    ]
    return {
        "order_id": sale.id,
        "payment_reference": sale.payment_reference,
        "customer": sale.customer,
        "shipping_address": sale.shipping_address or {},
        "total": str(sale.total),
        "currency": "COP",
        "service": service.name,
        "items": items,
    }


def _shipping_status_from_provider(raw_status: str | None) -> str:
    value = (raw_status or "").strip().lower()
    if value in {"created", "pending"}:
        return Shipment.ShipmentStatus.CREATED
    if value in {"in_transit", "picked_up"}:
        return Shipment.ShipmentStatus.IN_TRANSIT
    if value in {"delivered"}:
        return Shipment.ShipmentStatus.DELIVERED
    if value in {"failed", "exception"}:
        return Shipment.ShipmentStatus.FAILED
    if value in {"canceled", "cancelled"}:
        return Shipment.ShipmentStatus.CANCELED
    return Shipment.ShipmentStatus.CREATED


def _create_http_shipment(sale: Sale, service: ShippingServiceOption, *, source: str) -> Shipment:
    base_url = str(getattr(settings, "STORE_SHIPPING_API_BASE_URL", "")).strip().rstrip("/")
    create_path = str(getattr(settings, "STORE_SHIPPING_CREATE_PATH", "/shipments")).strip() or "/shipments"
    if not base_url:
        raise ShippingProviderError("STORE_SHIPPING_API_BASE_URL no esta configurado")

    auth_header = str(getattr(settings, "STORE_SHIPPING_AUTH_HEADER", "Authorization")).strip() or "Authorization"
    auth_prefix = str(getattr(settings, "STORE_SHIPPING_AUTH_PREFIX", "Bearer ")).strip()
    api_key = str(getattr(settings, "STORE_SHIPPING_API_KEY", "")).strip()
    headers: dict[str, str] = {}
    if api_key:
        headers[auth_header] = f"{auth_prefix}{api_key}"

    payload = _sale_payload_for_provider(sale, service)
    response = _http_json(
        f"{base_url}{create_path}",
        method="POST",
        payload=payload,
        headers=headers,
    )
    data = response.get("data") if isinstance(response, dict) and isinstance(response.get("data"), dict) else response
    if not isinstance(data, dict):
        raise ShippingProviderError("Respuesta invalida de transportadora")

    tracking_number = str(
        data.get("tracking_number")
        or data.get("tracking")
        or data.get("guide_number")
        or ""
    ).strip()
    if not tracking_number:
        raise ShippingProviderError("La transportadora no devolvio tracking_number")

    provider_reference = str(
        data.get("provider_reference")
        or data.get("reference")
        or data.get("id")
        or ""
    ).strip() or None
    carrier = str(data.get("carrier") or getattr(settings, "STORE_SHIPPING_CARRIER_NAME", "ExternalCarrier")).strip()
    service_name = str(data.get("service") or service.name).strip()
    label_url = str(data.get("label_url") or data.get("label") or "").strip() or None

    raw_cost = data.get("shipping_cost", data.get("cost", data.get("price", service.cost)))
    try:
        shipping_cost = Decimal(str(raw_cost))
    except Exception:
        shipping_cost = service.cost
    currency = str(data.get("currency") or "COP").strip() or "COP"
    shipment_status = _shipping_status_from_provider(data.get("status"))

    return Shipment.objects.create(
        sale=sale,
        carrier=carrier,
        service=service_name,
        tracking_number=tracking_number,
        provider_reference=provider_reference,
        label_url=label_url,
        shipping_cost=shipping_cost,
        currency=currency,
        status=shipment_status,
        created_by=source,
        metadata={"provider_response": data},
    )


def _create_mock_shipment(sale: Sale, service: ShippingServiceOption, *, source: str) -> Shipment:
    carrier_name = getattr(settings, "STORE_SHIPPING_CARRIER_NAME", "LocalCarrier")
    tracking_number = f"GLS-{uuid4().hex[:12].upper()}"
    provider_reference = f"{carrier_name[:3].upper()}-{uuid4().hex[:10].upper()}"
    label_url = f"https://labels.local/{tracking_number}.pdf"

    return Shipment.objects.create(
        sale=sale,
        carrier=carrier_name,
        service=service.name,
        tracking_number=tracking_number,
        provider_reference=provider_reference,
        label_url=label_url,
        shipping_cost=service.cost,
        currency="COP",
        status=Shipment.ShipmentStatus.CREATED,
        created_by=source,
        metadata={"eta_hours": service.eta_hours},
    )


def create_shipment_for_sale(sale: Sale, *, source: str = "store_api") -> Shipment:
    if not sale.is_order:
        raise ShippingProviderError("Solo se puede crear guia para ordenes")
    if sale.status == "canceled":
        raise ShippingProviderError("No se puede crear guia para una orden cancelada")

    existing = sale.shipments.exclude(status=Shipment.ShipmentStatus.CANCELED).first()
    if existing:
        return existing

    service = choose_best_service()
    mode = _provider_mode()
    if mode == "http":
        return _create_http_shipment(sale, service, source=source)
    if mode != "mock":
        raise ShippingProviderError(f"Proveedor de envio no soportado: {mode}")
    return _create_mock_shipment(sale, service, source=source)


def shipping_webhook_signature(payload: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest.lower()


def is_valid_shipping_webhook_signature(payload_dict: dict, provided_signature: str, secret: str) -> bool:
    if not provided_signature or not secret:
        return False
    payload = json.dumps(payload_dict, separators=(",", ":"), ensure_ascii=False)
    expected = shipping_webhook_signature(payload, secret)
    return hmac.compare_digest(provided_signature.lower(), expected)
