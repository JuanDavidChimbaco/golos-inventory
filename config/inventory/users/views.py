"""
Views para gestión de usuarios
"""
from rest_framework import viewsets, permissions
from django.contrib.auth.models import User, Group
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserManagementSerializer,
    GroupSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de usuarios
    
    - Admin: CRUD completo
    - Otros: Solo lectura
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserManagementSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de grupos
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.DjangoModelPermissions]
