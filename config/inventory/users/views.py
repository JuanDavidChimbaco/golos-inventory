"""
Views para gestión de usuarios
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User, Group
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserManagementSerializer,
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
        """Endpoint para obtener información del usuario actual"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


@extend_schema(tags=['Groups'])
class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de grupos
    
    - Lectura: Usuarios autenticados
    - Creación: Usuarios con permiso add_group
    - Actualización: Usuarios con permiso change_group
    - Eliminación: Usuarios con permiso delete_group
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]