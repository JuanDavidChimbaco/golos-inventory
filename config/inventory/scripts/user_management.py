"""
Ejemplos de gestión de usuarios con múltiples grupos
"""

from django.contrib.auth.models import User, Group

def create_multi_role_user(username, email, password, groups):
    """
    Crea un usuario con múltiples grupos
    
    Args:
        username: Nombre de usuario
        email: Email del usuario
        password: Contraseña
        groups: Lista de nombres de grupos ['Sales', 'Inventory']
    """
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )
    
    # Asignar múltiples grupos
    for group_name in groups:
        try:
            group = Group.objects.get(name=group_name)
            user.groups.add(group)
            print(f"✅ Usuario '{username}' agregado al grupo '{group_name}'")
        except Group.DoesNotExist:
            print(f"❌ Grupo '{group_name}' no encontrado")
    
    return user

def assign_user_to_groups(username, groups):
    """
    Asigna un usuario existente a múltiples grupos
    
    Args:
        username: Nombre de usuario existente
        groups: Lista de nombres de grupos ['Sales', 'Inventory']
    """
    try:
        user = User.objects.get(username=username)
        
        # Limpiar grupos existentes (opcional)
        # user.groups.clear()
        
        # Agregar a nuevos grupos
        for group_name in groups:
            try:
                group = Group.objects.get(name=group_name)
                user.groups.add(group)
                print(f"✅ Usuario '{username}' agregado al grupo '{group_name}'")
            except Group.DoesNotExist:
                print(f"❌ Grupo '{group_name}' no encontrado")
                
        # Mostrar grupos actuales
        current_groups = [g.name for g in user.groups.all()]
        print(f"📋 Grupos actuales de '{username}': {current_groups}")
        
        return user
    except User.DoesNotExist:
        print(f"❌ Usuario '{username}' no encontrado")
        return None

def check_user_permissions(username):
    """
    Muestra todos los permisos de un usuario
    """
    try:
        user = User.objects.get(username=username)
        
        print(f"🔍 Permisos de '{username}':")
        
        # Permisos por grupos
        for group in user.groups.all():
            print(f"\n📂 Grupo: {group.name}")
            for perm in group.permissions.all():
                print(f"  ✅ {perm.codename} - {perm.name}")
        
        # Verificar permisos específicos
        key_permissions = [
            'inventory.view_product',
            'inventory.add_product',
            'inventory.delete_product',
            'inventory.view_sale',
            'inventory.add_sale',
            'inventory.confirm_sale',
            'inventory.manage_inventory',
        ]
        
        print(f"\n🎯 Verificación de permisos clave:")
        for perm in key_permissions:
            has_perm = user.has_perm(perm)
            status = "✅" if has_perm else "❌"
            print(f"  {status} {perm}")
            
    except User.DoesNotExist:
        print(f"❌ Usuario '{username}' no encontrado")


# Ejemplos de uso:
if __name__ == "__main__":
    # Crear usuario con múltiples roles
    create_multi_role_user(
        username="juan_ventas_inventario",
        email="juan@ejemplo.com", 
        password="temporal123",
        groups=["Sales", "Inventory"]
    )
    
    # Asignar usuario existente a múltiples grupos
    assign_user_to_groups(
        username="juan_ventas_inventario",
        groups=["Sales", "Inventory"]
    )
    
    # Verificar permisos
    check_user_permissions("juan_ventas_inventario")
