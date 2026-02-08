"""
Módulo core - Funcionalidades compartidas
"""

# Importaciones de configuración
from .constants import GROUP_SALES, GROUP_INVENTORY, GROUP_MANAGERS

# Importaciones de servicios
from .services import (
    ImageService,
    confirm_sale,
)

__all__ = [
    # Grupos de usuarios
    'GROUP_SALES',
    'GROUP_INVENTORY', 
    'GROUP_MANAGERS',
    
    # Servicios
    'ImageService',
    'confirm_sale',
    'create_purchase',
    'create_adjustment', 
    'create_sale_return',
    'create_supplier_return',
    
    # Utilidades - Archivos
    'get_file_size_mb',
    'get_file_extension',
    'generate_unique_filename',
    
    # Utilidades - Fechas
    'get_date_range',
    'format_date',
    
    # Utilidades - Cálculos
    'calculate_profit_margin',
    'calculate_total_amount',
    'apply_discount',
    
    # Utilidades - Validaciones
    'validate_positive_number',
    'validate_email_format',
    'validate_phone_number',
    
    # Utilidades - Strings
    'normalize_string',
    'generate_slug',
    'truncate_string',
    
    # Utilidades - Business
    'get_stock_status',
    'calculate_reorder_point',
    'format_currency',
    
    # Utilidades - Sistema
    'get_client_ip',
    'is_development',
    'get_app_version',
    
    # Utilidades - Logging
    'log_user_action',
    'log_system_event',
]
