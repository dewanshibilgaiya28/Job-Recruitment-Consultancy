# main/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from .utils import get_user_role  # make sure get_user_role is importable

def role_required(role_attr):
    """
    Decorator to check if the logged-in user has a certain role.
    Example: role_required('candidate') or role_required('client')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request.user, role_attr):
                messages.error(request, "You do not have access to this page.")
                if request.user.is_authenticated:
                    return redirect("dashboard")
                return redirect("login")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def custom_role_required(allowed_roles):
    """
    Decorator to check for roles stored in your Stakeholder model (like RECRUITER, ADMIN)
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role not in allowed_roles:
                messages.error(request, "You do not have access to this page.")
                if request.user.is_authenticated:
                    return redirect("dashboard")
                return redirect("login")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
