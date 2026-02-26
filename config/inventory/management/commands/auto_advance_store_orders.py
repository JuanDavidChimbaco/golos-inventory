from django.core.management.base import BaseCommand

from inventory.store.automation import auto_advance_store_orders


class Command(BaseCommand):
    help = "Avanza automaticamente estados de ordenes de tienda (paid->processing->shipped->delivered->completed)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra cuantas ordenes aplicarian sin persistir cambios.",
        )

    def handle(self, *args, **options):
        summary = auto_advance_store_orders(dry_run=options["dry_run"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Auto-advance ejecutado. Procesadas: {summary['processed']}. Actualizadas: {summary['updated']}."
            )
        )
