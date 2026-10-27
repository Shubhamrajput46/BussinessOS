from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def role_required(*allowed_roles):
    """Restrict a view to the given roles.

    Anonymous users go to the login page; authenticated users with the
    wrong role are sent back to the dashboard with an explanation.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")

            if request.user.role not in allowed_roles:
                messages.error(request, "You do not have permission to do that.")
                return redirect("dashboard")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
