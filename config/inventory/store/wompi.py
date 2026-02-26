"""
Helpers de integracion con Wompi.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib import error, request
from urllib.parse import quote

from django.conf import settings


class WompiError(Exception):
    """Error de integracion con Wompi."""


def amount_to_cents(amount: str) -> int:
    return int(round(float(amount) * 100))


def build_integrity_signature(reference: str, amount_in_cents: int, currency: str = "COP") -> str:
    payload = f"{reference}{amount_in_cents}{currency}{settings.WOMPI_INTEGRITY_SECRET}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_checkout_url(
    *,
    reference: str,
    amount_in_cents: int,
    redirect_url: str,
    currency: str = "COP",
) -> str:
    signature = build_integrity_signature(reference, amount_in_cents, currency)
    params = {
        "public-key": settings.WOMPI_PUBLIC_KEY,
        "currency": currency,
        "amount-in-cents": str(amount_in_cents),
        "reference": reference,
        "redirect-url": redirect_url,
        "signature:integrity": signature,
    }
    query = "&".join([f"{key}={quote(value, safe='')}" for key, value in params.items()])
    return f"{settings.WOMPI_CHECKOUT_BASE_URL}?{query}"


def _http_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = request.Request(url=url, headers=headers or {}, method="GET")
    try:
        with request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise WompiError(f"HTTP {exc.code}: {detail}")
    except Exception as exc:
        raise WompiError(str(exc))


def get_transaction(transaction_id: str) -> dict[str, Any]:
    url = f"{settings.WOMPI_API_BASE_URL}/transactions/{transaction_id}"
    return _http_json(url)


def extract_event_signature_payload(event_data: dict[str, Any], properties: list[str]) -> str:
    """
    Construye la cadena para validar firma de eventos usando paths de properties.
    """
    fragments: list[str] = []
    for path in properties:
        value: Any = event_data
        for key in path.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break
        if value is None:
            value = ""
        fragments.append(str(value))
    fragments.append(settings.WOMPI_EVENTS_SECRET)
    return "".join(fragments)
