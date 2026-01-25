from django.contrib.auth.models import User, Group
from rest_framework import serializers


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Group.objects.all(), required=False
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "is_staff",
            "groups",
        ]

    def create(self, validated_data):
        groups_data = validated_data.pop("groups", [])
        password = validated_data.pop("password")

        user = User.objects.create_user(password=password, **validated_data)

        if groups_data:
            user.groups.set(groups_data)

        return user


class UserManagementSerializer(serializers.ModelSerializer):
    groups = serializers.StringRelatedField(many=True, read_only=True)
    user_permissions = serializers.StringRelatedField(many=True, read_only=True)

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
            "last_login",
            "groups",
            "user_permissions",
        ]


class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]
