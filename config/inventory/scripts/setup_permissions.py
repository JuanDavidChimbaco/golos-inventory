"""
Script para configurar grupos y permisos.
Uso:
    python manage.py shell < scripts/setup_permissions.py
"""

from django.contrib.auth.models import Group, Permission


def setup_groups_and_permissions() -> None:
    groups_data = {
        "Sales": [
            "inventory.view_product",
            "inventory.view_sale",
            "inventory.add_sale",
            "inventory.change_sale",
            "inventory.confirm_sale",
        ],
        "Inventory": [
            "inventory.view_product",
            "inventory.add_product",
            "inventory.change_product",
            "inventory.view_movementinventory",
            "inventory.add_movementinventory",
            "inventory.change_movementinventory",
            "inventory.manage_inventory",
        ],
        "Customers": [
            "inventory.view_product",
            "inventory.add_sale",
            "inventory.view_sale",
        ],
        "StoreOps": [
            "inventory.view_product",
            "inventory.view_sale",
            "inventory.change_sale",
        ],
        "Managers": [
            "inventory.view_product",
            "inventory.add_product",
            "inventory.change_product",
            "inventory.delete_product",
            "inventory.view_sale",
            "inventory.add_sale",
            "inventory.change_sale",
            "inventory.delete_sale",
            "inventory.confirm_sale",
            "inventory.view_movementinventory",
            "inventory.add_movementinventory",
            "inventory.change_movementinventory",
            "inventory.delete_movementinventory",
            "inventory.manage_inventory",
            "auth.view_user",
            "auth.add_user",
            "auth.change_user",
            "auth.view_group",
            "auth.add_group",
            "auth.change_group",
        ],
    }

    print("Configurando grupos y permisos...")
    for group_name, permission_codes in groups_data.items():
        group, created = Group.objects.get_or_create(name=group_name)
        print(f"{'Creado' if created else 'Actualizado'} grupo: {group_name}")
        group.permissions.clear()

        for permission_code in permission_codes:
            codename = permission_code.split(".")[-1]
            permission = Permission.objects.filter(
                codename=codename,
                content_type__app_label=permission_code.split(".")[0],
            ).first()
            if not permission:
                permission = Permission.objects.filter(codename=codename).first()
            if not permission:
                print(f"  [WARN] Permiso no encontrado: {permission_code}")
                continue
            group.permissions.add(permission)
            print(f"  [OK] {permission_code}")

        group.save()

    print("Configuracion completada.")


setup_groups_and_permissions()
