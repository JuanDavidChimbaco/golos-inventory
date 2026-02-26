"""
Serializers para gestión de usuarios y grupos
"""
from django.contrib.auth.models import User, Group, Permission
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    """Serializer básico para usuarios"""
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear nuevos usuarios"""
    password = serializers.CharField(write_only=True, min_length=8)
    groups = serializers.SerializerMethodField(read_only=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        many=True,
        required=False,
        source="groups",
    )
    
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "is_staff",
            "groups",
            "group_ids",
        ]

    def get_groups(self, obj):
        return [{"id": group.id, "name": group.name} for group in obj.groups.all()]
    
    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        if groups:
            user.groups.set(groups)
        return user


class UserManagementSerializer(serializers.ModelSerializer):
    """Serializer para gestionar usuarios existentes"""
    groups = serializers.SerializerMethodField(read_only=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        many=True,
        required=False,
        source="groups",
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "date_joined",
            "groups",
            "group_ids",
        ]
        read_only_fields = ["id", "date_joined"]

    def get_groups(self, obj):
        return [{"id": group.id, "name": group.name} for group in obj.groups.all()]


class UserMeSerializer(serializers.ModelSerializer):
    """Serializer para perfil propio"""
    groups = serializers.SerializerMethodField()

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_staff", "is_active", "groups"]
        read_only_fields = ["id", "username", "is_staff", "is_active"]


class UserMePasswordSerializer(serializers.Serializer):
    """Serializer para cambio de contraseña del usuario actual"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual no es correcta.")
        return value


class GroupSerializer(serializers.ModelSerializer):
    """Serializer para gestión de grupos"""
    permissions = serializers.SerializerMethodField(read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source="permissions",
    )

    def get_permissions(self, obj):
        return [
            {
                "id": perm.id,
                "name": perm.name,
                "codename": perm.codename,
                "content_type": perm.content_type_id,
                "content_type_name": perm.content_type.model,
            }
            for perm in obj.permissions.all()
        ]

    class Meta:
        model = Group
        fields = ["id", "name", "permissions", "permission_ids"]
