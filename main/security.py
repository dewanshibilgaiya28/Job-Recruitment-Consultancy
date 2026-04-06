# main/security.py
"""
Security utilities for the recruitment system including rate limiting,
XSS prevention, and security headers.
"""

from django.utils.decorators import decorator_from_middleware
from django.http import JsonResponse, HttpResponse
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils.html import escape
from functools import wraps
from datetime import datetime, timedelta
import hashlib
import json

# Rate limiting constants
RATE_LIMITS = {
    'auth': {'attempts': 5, 'period': 60},  # 5 per minute
    'job_posting': {'attempts': 10, 'period': 60},  # 10 per minute
    'application': {'attempts': 10, 'period': 60},  # 10 per minute
    'search': {'attempts': 60, 'period': 60},  # 60 per minute
}


class RateLimitError(Exception):
    """Custom exception for rate limit exceeded"""
    pass


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_rate_limit_key(request, action):
    """Generate a unique rate limit key per user/IP and action"""
    if request.user.is_authenticated:
        identifier = f"user_{request.user.id}"
    else:
        identifier = f"ip_{get_client_ip(request)}"
    return f"rate_limit_{action}_{identifier}"


def check_rate_limit(request, action):
    """Check if the user/IP has exceeded rate limits"""
    if action not in RATE_LIMITS:
        return True
    
    config = RATE_LIMITS[action]
    key = get_rate_limit_key(request, action)
    
    current = cache.get(key, 0)
    if current >= config['attempts']:
        return False
    
    cache.set(key, current + 1, config['period'])
    return True


def rate_limit_view(action='search'):
    """Decorator to enforce rate limiting on views"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not check_rate_limit(request, action):
                return JsonResponse(
                    {'error': 'Rate limit exceeded. Please try again later.'},
                    status=429
                )
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def sanitize_html(unsafe_string):
    """Sanitize user input to prevent XSS attacks"""
    return escape(unsafe_string)


def sanitize_input(input_dict, max_length=500):
    """Sanitize a dictionary of inputs"""
    sanitized = {}
    for key, value in input_dict.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_html(value[:max_length] if len(value) > max_length else value)
        else:
            sanitized[key] = value
    return sanitized


class AuditLog:
    """Simple audit logging for security-sensitive operations"""
    
    @staticmethod
    def log_action(user, action, resource_type, resource_id, details=None, status='success'):
        """Log security-sensitive actions"""
        from .models import AuditLog as AuditLogModel
        try:
            AuditLogModel.objects.create(
                user=user,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=json.dumps(details) if details else None,
                status=status,
                ip_address=None  # Will be set by middleware
            )
        except Exception as e:
            print(f"Failed to log action: {e}")


def generate_password_hash_strength(password):
    """Evaluate password strength"""
    score = 0
    
    if len(password) >= 12:
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        score += 1
    
    strength_levels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong']
    return {
        'score': score,
        'strength': strength_levels[score],
        'is_strong': score >= 3
    }


def validate_email_format(email):
    """Validate email format using regex"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone_format(phone):
    """Validate phone format"""
    import re
    pattern = r'^[\d\s\-\+\(\)]{10,}$'
    return re.match(pattern, phone) is not None
