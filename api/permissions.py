from rest_framework.permissions import BasePermission


class HasRolePermission(BasePermission):
    """Method-wise role matrix declared on the view as ``role_permissions``."""

    message = "Your role is not allowed to perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not getattr(user, "organisation_id", None):
            return False

        role_permissions = getattr(view, "role_permissions", {})
        method = "GET" if request.method in ("HEAD", "OPTIONS") else request.method
        return user.role in role_permissions.get(method, [])
