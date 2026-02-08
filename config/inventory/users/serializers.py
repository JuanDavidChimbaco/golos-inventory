"""
Serializers para gestión de usuarios y grupos
"""
from django.contrib.auth.models import User, Group
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    """Serializer básico para usuarios"""
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear nuevos usuarios"""
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ["username", "email", "password", "is_staff"]
    
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserManagementSerializer(serializers.ModelSerializer):
    """Serializer para gestionar usuarios existentes"""
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff", "is_active", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class GroupSerializer(serializers.ModelSerializer):
    """Serializer para gestión de grupos"""
    class Meta:
        model = Group
        fields = ["id", "name"]
