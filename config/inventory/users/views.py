"""
Views para gestión de usuarios
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User, Group, Permission
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserManagementSerializer,
    UserMeSerializer,
    UserMePasswordSerializer,
    GroupSerializer,
)
from drf_spectacular.utils import extend_schema

@extend_schema(tags=['Users'])
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de usuarios
    
    - Lectura: Usuarios autenticados
    - Creación: Usuarios con permiso add_user
    - Actualización: Usuarios con permiso change_user
    - Eliminación: Usuarios con permiso delete_user
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.request.user.is_staff:
            return UserManagementSerializer  # Campos administrativos para staff
        return UserSerializer  # Campos básicos para usuarios normales

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Endpoint para obtener/actualizar información del usuario actual"""
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data)

    @me.mapping.patch
    def me_patch(self, request):
        serializer = UserMeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='me/change-password', permission_classes=[permissions.IsAuthenticated])
    def change_my_password(self, request):
        serializer = UserMePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Contraseña actualizada correctamente."}, status=status.HTTP_200_OK)


@extend_schema(tags=['Groups'])
class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de grupos
    
    - Lectura: Usuarios autenticados
    - Creación: Usuarios con permiso add_group
    - Actualización: Usuarios con permiso change_group
    - Eliminación: Usuarios con permiso delete_group
    """
    queryset = Group.objects.prefetch_related("permissions__content_type").all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]


@extend_schema(tags=['Permissions'])
class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para catálogo de permisos.
    """
    queryset = Permission.objects.select_related("content_type").all().order_by("content_type__app_label", "codename")
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(content_type__app_label="inventory")
        page = self.paginate_queryset(queryset)
        if page is not None:
            data = [
                {
                    "id": perm.id,
                    "name": perm.name,
                    "codename": perm.codename,
                    "content_type": perm.content_type_id,
                    "content_type_name": perm.content_type.model,
                }
                for perm in page
            ]
            return self.get_paginated_response(data)

        data = [
            {
                "id": perm.id,
                "name": perm.name,
                "codename": perm.codename,
                "content_type": perm.content_type_id,
                "content_type_name": perm.content_type.model,
            }
            for perm in queryset
        ]
        return Response(data)
