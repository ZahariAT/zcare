from rest_framework import permissions


class IsStuffOrReadOnly(permissions.BasePermission):
    """
    Allows access only to staff users, or is a read-only request.
    """

    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS or request.user and request.user.is_authenticated and request.user.is_staff)


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to admins/superusers.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
