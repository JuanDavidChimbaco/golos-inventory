"""
Script para configurar permisos y grupos iniciales
Ejecutar con: python manage.py shell < setup_permissions.py
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from inventory.models import Product, Sale, MovementInventory


def setup_groups_and_permissions():
    """Configura grupos y asigna permisos"""
    
    # Obtener o crear grupos
    groups_data = {
        'Sales': {
            'description': 'Usuarios de ventas',
            'permissions': [
                # Permisos automáticos de Django
                'inventory.view_product',
                'inventory.view_sale', 
                'inventory.add_sale',
                'inventory.change_sale',
                # Permisos personalizados
                'inventory.confirm_sale',
            ]
        },
        'Inventory': {
            'description': 'Usuarios de inventario',
            'permissions': [
                # Permisos automáticos de Django
                'inventory.view_product',
                'inventory.add_product',
                'inventory.change_product',
                'inventory.view_movementinventory',
                'inventory.add_movementinventory',
                'inventory.change_movementinventory',
                # Permisos personalizados
                'inventory.manage_inventory',
            ]
        },
        'Customers': {
            'description': 'Clientes de e-commerce',
            'permissions': [
                # Solo pueden ver productos y crear ventas
                'inventory.view_product',
                'inventory.add_sale',
                'inventory.view_sale',
                # No pueden modificar ni confirmar ventas
            ]
        },
        'Managers': {
            'description': 'Administradores del sistema',
            'permissions': [
                # Todos los permisos de productos
                'inventory.view_product',
                'inventory.add_product',
                'inventory.change_product', 
                'inventory.delete_product',
                # Todos los permisos de ventas
                'inventory.view_sale',
                'inventory.add_sale',
                'inventory.change_sale',
                'inventory.delete_sale',
                'inventory.confirm_sale',
                # Todos los permisos de inventario
                'inventory.view_movementinventory',
                'inventory.add_movementinventory',
                'inventory.change_movementinventory',
                'inventory.delete_movementinventory',
                'inventory.manage_inventory',
                # Permisos de gestión de usuarios y grupos
                'auth.view_user',
                'auth.add_user',
                'auth.change_user',
                'auth.view_group',
                'auth.add_group',
                'auth.change_group',
            ]
        }
    }
    
    print("🔧 Configurando grupos y permisos...")
    
    for group_name, group_info in groups_data.items():
        # Crear o obtener el grupo
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            print(f"✅ Grupo '{group_name}' creado")
        else:
            print(f"📋 Grupo '{group_name}' ya existe")
        
        # Limpiar permisos existentes del grupo
        group.permissions.clear()
        
        # Asignar permisos al grupo
        for perm_codename in group_info['permissions']:
            try:
                # Buscar el permiso por codename exacto
                permissions = Permission.objects.filter(codename=perm_codename.split('.')[-1])
                if permissions.exists():
                    # Si hay múltiples, tomar el primero del app inventory
                    permission = permissions.filter(content_type__app_label='inventory').first()
                    if not permission:
                        permission = permissions.first()
                    group.permissions.add(permission)
                    print(f"  ✅ Permiso '{perm_codename}' asignado a '{group_name}'")
                else:
                    print(f"  ❌ Permiso '{perm_codename}' no encontrado")
            except Exception as e:
                print(f"  ❌ Error con permiso '{perm_codename}': {e}")
        
        group.save()
    
    print("\n🎉 Configuración de permisos completada!")
    
    # Mostrar resumen
    print("\n📊 Resumen de grupos y permisos:")
    for group_name in groups_data.keys():
        group = Group.objects.get(name=group_name)
        perms = [p.codename for p in group.permissions.all()]
        print(f"🔸 {group_name}: {len(perms)} permisos")
        for perm in perms:
            print(f"   - {perm}")


if __name__ == "__main__":
    setup_groups_and_permissions()
