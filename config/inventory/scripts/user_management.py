"""
Utilidades de gestion de usuarios y grupos para operaciones.
"""

from __future__ import annotations

from django.contrib.auth.models import Group, User


def assign_user_to_groups(username: str, groups: list[str]) -> dict:
    user = User.objects.filter(username=username).first()
    if not user:
        raise ValueError(f"Usuario no encontrado: {username}")

    assigned: list[str] = []
    missing: list[str] = []
    for group_name in groups:
        group = Group.objects.filter(name=group_name).first()
        if not group:
            missing.append(group_name)
            continue
        user.groups.add(group)
        assigned.append(group_name)

    return {"username": username, "assigned_groups": assigned, "missing_groups": missing}


def check_user_permissions(username: str) -> dict:
    user = User.objects.filter(username=username).first()
    if not user:
        raise ValueError(f"Usuario no encontrado: {username}")

    groups = list(user.groups.values_list("name", flat=True))
    permissions = sorted(user.get_all_permissions())
    return {"username": username, "groups": groups, "permissions": permissions, "is_superuser": user.is_superuser}


def create_multi_role_user(
    *,
    username: str,
    email: str,
    password: str,
    groups: list[str] | None = None,
    is_staff: bool = False,
) -> dict:
    if User.objects.filter(username=username).exists():
        raise ValueError(f"El usuario {username} ya existe")

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        is_staff=is_staff,
    )

    result = {"username": username, "created": True, "assigned_groups": [], "missing_groups": []}
    if groups:
        assignment = assign_user_to_groups(username, groups)
        result["assigned_groups"] = assignment["assigned_groups"]
        result["missing_groups"] = assignment["missing_groups"]
    return result
