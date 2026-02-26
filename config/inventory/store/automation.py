"""
Reglas de automatizacion para avanzar estados de ordenes de tienda.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import AuditLog, Sale


@dataclass(frozen=True)
class TransitionRule:
    from_status: str
    to_status: str
    source_datetime_field: str
    threshold_minutes: int
    target_datetime_field: str | None = None


DEFAULT_TRANSITION_RULES = (
    TransitionRule("paid", "processing", "paid_at", threshold_minutes=5, target_datetime_field="confirmed_at"),
    TransitionRule("processing", "shipped", "confirmed_at", threshold_minutes=120, target_datetime_field="shipped_at"),
    TransitionRule("shipped", "delivered", "shipped_at", threshold_minutes=1440, target_datetime_field="delivered_at"),
    TransitionRule("delivered", "completed", "delivered_at", threshold_minutes=2880),
)


def _rule_threshold_minutes(rule: TransitionRule) -> int:
    setting_map = {
        "processing": "STORE_AUTO_TO_PROCESSING_MINUTES",
        "shipped": "STORE_AUTO_TO_SHIPPED_MINUTES",
        "delivered": "STORE_AUTO_TO_DELIVERED_MINUTES",
        "completed": "STORE_AUTO_TO_COMPLETED_MINUTES",
    }
    setting_name = setting_map.get(rule.to_status)
    configured_value = getattr(settings, setting_name, rule.threshold_minutes) if setting_name else rule.threshold_minutes
    try:
        parsed = int(configured_value)
    except (TypeError, ValueError):
        return rule.threshold_minutes
    return max(parsed, 0)


@transaction.atomic
def auto_advance_store_orders(*, dry_run: bool = False) -> dict[str, int]:
    """
    Avanza ordenes por etapas segun timestamps y umbrales.
    Solo aplica una transicion por orden en cada ejecucion.
    """
    if not getattr(settings, "STORE_AUTO_ADVANCE_ENABLED", True):
        return {"processed": 0, "updated": 0}

    now = timezone.now()
    processed = 0
    updated = 0
    transitioned_ids: set[int] = set()

    for rule in DEFAULT_TRANSITION_RULES:
        threshold_minutes = _rule_threshold_minutes(rule)
        cutoff = now - timedelta(minutes=threshold_minutes)

        queryset = Sale.objects.select_for_update().filter(
            is_order=True,
            status=rule.from_status,
            **{
                f"{rule.source_datetime_field}__isnull": False,
                f"{rule.source_datetime_field}__lte": cutoff,
            },
        )
        if transitioned_ids:
            queryset = queryset.exclude(id__in=transitioned_ids)

        for sale in queryset:
            processed += 1
            transitioned_ids.add(sale.id)
            if dry_run:
                continue

            fields_to_update = ["status", "updated_at"]
            sale.status = rule.to_status

            if rule.target_datetime_field and not getattr(sale, rule.target_datetime_field):
                setattr(sale, rule.target_datetime_field, now)
                fields_to_update.append(rule.target_datetime_field)

            sale.save(update_fields=fields_to_update)
            AuditLog.objects.create(
                action="store_order_status_auto_advance",
                entity="sale",
                entity_id=sale.id,
                performed_by="store_automation",
                extra_data={
                    "from_status": rule.from_status,
                    "to_status": rule.to_status,
                    "threshold_minutes": threshold_minutes,
                },
            )
            updated += 1

    return {"processed": processed, "updated": updated}
