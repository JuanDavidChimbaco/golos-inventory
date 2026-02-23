from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = 'inventory'

class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales'
    
    def ready(self):
        import core.signals
        return super().ready()