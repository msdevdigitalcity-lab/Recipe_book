from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminRole(BasePermission):
    """Allow access only to users with admin role or Django superusers."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_admin_role()
        )


class IsOwnerOrAdminOrReadOnly(BasePermission):
    """
    Read: anyone.
    Write: owner of the object, or admin role.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        owner = getattr(obj, 'author', None) or getattr(obj, 'user', None)
        return owner == request.user or request.user.is_admin_role()
