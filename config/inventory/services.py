from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from .models import MovementInventory, Sale


def confirm_sale(sale_id: int, user: User) -> None:
    with transaction.atomic():
        # Traer la venta con bloqueo para evitar concurrentes
        sale = Sale.objects.select_for_update().get(id=sale_id)

        # Validaciones basicas
        if sale.status != "pending":
            raise ValidationError("La venta no está pendiente")

        details = sale.details.select_related("variant").all()
        if not details:
            raise ValidationError("La venta no tiene Productos")

        # validar stock por variante
        for detail in details:
            stock = (
                detail.variant.movements.aggregate(total=Sum("quantity"))["total"] or 0
            )
            if stock < detail.quantity:
                raise ValidationError(
                    f"Stock insuficiente para el producto {detail.variant.product.name}"
                )

        # confirmar venta
        sale.status = "completed"
        sale.created_by = user.username
        sale.save()

        # crear movimientos
        movements = []
        for detail in details:
            movements.append(
                MovementInventory(
                    variant=detail.variant,
                    movement_type="sale",
                    quantity=-detail.quantity,
                    created_by=user.username,
                )
            )
        MovementInventory.objects.bulk_create(movements)
