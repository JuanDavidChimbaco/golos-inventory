"""
Comando de Django para gestión de usuarios con múltiples grupos
Ejecutar con: python manage.py create_user --username=testuser --email=test@example.com --groups=Sales,Inventory
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from inventory.management.commands.setup_permissions import Command as SetupCommand


class Command(BaseCommand):
    help = 'Crea usuarios con asignación a múltiples grupos'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Nombre de usuario')
        parser.add_argument('--email', required=True, help='Email del usuario')
        parser.add_argument('--password', help='Contraseña (opcional, se pedirá si no se proporciona)')
        parser.add_argument('--groups', required=True, help='Grupos separados por coma (ej: Sales,Inventory)')
        parser.add_argument('--superuser', action='store_true', help='Crear como superusuario')
        parser.add_argument('--staff', action='store_true', help='Marcar como staff')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        groups_str = options['groups']
        is_superuser = options['superuser']
        is_staff = options['staff']

        # Verificar que los grupos existan
        group_names = [g.strip() for g in groups_str.split(',')]
        existing_groups = []

        for group_name in group_names:
            try:
                group = Group.objects.get(name=group_name)
                existing_groups.append(group)
            except Group.DoesNotExist:
                raise CommandError(f"Grupo '{group_name}' no existe. Ejecuta setup_permissions primero.")

        # Pedir contraseña si no se proporcionó
        if not password:
            import getpass
            password = getpass.getpass('Contraseña: ')
            if not password:
                raise CommandError('La contraseña es requerida')

        # Crear usuario
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            if is_superuser:
                user.is_superuser = True
            if is_staff:
                user.is_staff = True
            user.save()

            # Asignar grupos
            for group in existing_groups:
                user.groups.add(group)
                self.stdout.write(f"✅ Usuario '{username}' agregado al grupo '{group.name}'")

            self.stdout.write(self.style.SUCCESS(f"✅ Usuario '{username}' creado exitosamente"))

            # Mostrar resumen
            current_groups = [g.name for g in user.groups.all()]
            self.stdout.write(f"📋 Grupos asignados: {', '.join(current_groups)}")

        except Exception as e:
            raise CommandError(f"Error al crear usuario: {e}")
