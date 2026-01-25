from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permite acceso completo a administradores, solo lectura a otros usuarios autenticados.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permite acceso solo al dueño del objeto o administradores.
    """

    def has_object_permission(self, request, view, obj):
        # Administradores tienen acceso completo
        if request.user.is_staff:
            return True

        # Verificar si el objeto tiene campo created_by
        if hasattr(obj, "created_by"):
            return obj.created_by == request.user.username

        # Verificar si el objeto tiene campo user
        if hasattr(obj, "user"):
            return obj.user == request.user

        return False


class IsSalesUserOrAdmin(permissions.BasePermission):
    """
    Permite acceso a usuarios de ventas y administradores.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff
            or getattr(request.user, "is_sales_user", False)
            or request.user.groups.filter(name="Sales").exists()
        )


class IsInventoryUserOrAdmin(permissions.BasePermission):
    """
    Permite acceso a usuarios de inventario y administradores.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff
            or getattr(request.user, "is_inventory_user", False)
            or request.user.groups.filter(name="Inventory").exists()
        )


class CanConfirmSales(permissions.BasePermission):
    """
    Permite confirmar ventas solo a usuarios autorizados.
    """

    def has_permission(self, request, view):
        if view.action != "confirm":
            return True

        return request.user.is_authenticated and (
            request.user.is_staff
            or getattr(request.user, "can_confirm_sales", False)
            or request.user.groups.filter(name__in=["Sales", "Managers"]).exists()
        )
