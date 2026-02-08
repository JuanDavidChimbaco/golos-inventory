"""
Scripts de utilidad para Golos Inventory
"""

# Importaciones de configuración
from .setup_permissions import setup_groups_and_permissions

# Importaciones de gestión de usuarios
from .user_management import (
    create_multi_role_user,
    assign_user_to_groups,
    check_user_permissions,
)

# Importaciones de integración e-commerce
from .ecommerce_integration import ECommerceCustomer

__all__ = [
    # Configuración
    'setup_groups_and_permissions',
    
    # Gestión de usuarios
    'create_multi_role_user',
    'assign_user_to_groups', 
    'check_user_permissions',
    
    # E-commerce
    'ECommerceCustomer',
]
