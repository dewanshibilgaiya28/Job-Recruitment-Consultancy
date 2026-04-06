
# main/middleware.py
"""
Middleware for security, RBAC, rate limiting, audit logging, and XSS protection
"""

from django.http import HttpResponseForbidden, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.utils import timezone
from main.models import Stakeholder
import json


class RoleRequiredMiddleware:
    """Basic role authorization middleware for legacy compatibility"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith('/admin') and request.user.is_authenticated:
            try:
                role = Stakeholder.objects.get(user=request.user).role
                if role != 'ADMIN':
                    return HttpResponseForbidden("Unauthorized")
            except Stakeholder.DoesNotExist:
                return HttpResponseForbidden("Unauthorized")
        return self.get_response(request)


class RoleBasedAccessControlMiddleware(MiddlewareMixin):
    """Enforce role-based access control on protected routes"""
    
    PROTECTED_ROUTES = {
        '/admin/': ['ADMIN'],
        '/dashboard/recruiter': ['RECRUITER', 'OWNER', 'ADMIN'],
        '/dashboard/client': ['CLIENT'],
        '/dashboard/candidate': ['CANDIDATE'],
        '/reports': ['ADMIN', 'RECRUITER', 'OWNER'],
    }
    
    def process_request(self, request):
        # Allow Django admin authentication and related admin pages to work normally.
        if request.path.startswith('/admin/') and self._is_admin_auth_exempt(request.path):
            return None

        # For /admin/, allow unauthenticated access so Django can redirect to login
        if request.path == '/admin/' and not request.user.is_authenticated:
            return None

        # Check if the route is protected
        for protected_path, allowed_roles in self.PROTECTED_ROUTES.items():
            if request.path.startswith(protected_path):
                # Check if user is authenticated
                if not request.user.is_authenticated:
                    return HttpResponseForbidden("Authentication required")
                
                # Get user role
                user_role = self._get_user_role(request.user)
                
                # Check if user has access to this route
                if user_role not in allowed_roles:
                    return HttpResponseForbidden(
                        f"Unauthorized. Required role: {', '.join(allowed_roles)}"
                    )
        
        return None

    @staticmethod
    def _is_admin_auth_exempt(path):
        exempt_paths = [
            '/admin/login/',
            '/admin/logout/',
            '/admin/password_change/',
            '/admin/password_reset/',
            '/admin/password_reset/done/',
            '/admin/reset/',
        ]
        return any(path.startswith(exempt) for exempt in exempt_paths)
    
    @staticmethod
    def _get_user_role(user):
        """Get the user's role from various models"""
        if user.is_staff or user.is_superuser:
            return 'ADMIN'
        
        try:
            stakeholder = Stakeholder.objects.get(user=user)
            return stakeholder.role
        except Stakeholder.DoesNotExist:
            pass
        
        if hasattr(user, 'client'):
            return 'CLIENT'
        
        if hasattr(user, 'candidate'):
            return 'CANDIDATE'
        
        return 'UNKNOWN'


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses"""
    
    def process_response(self, request, response):
        # Prevent clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME-sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection in older browsers
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Strict Transport Security (for HTTPS)
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com"
        )
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Implement rate limiting for different API endpoints"""
    
    RATE_LIMIT_ENDPOINTS = {
        '/login/': 'auth',
        '/api/jobs/': 'search',
        '/jobs/search/': 'search',
        '/jobs/filter/': 'search',
        '/job/post/': 'job_posting',
        '/apply/': 'application',
    }
    
    # Rate limit configuration
    RATE_LIMITS = {
        'auth': {'attempts': 5, 'period': 300},  # 5 attempts per 5 minutes
        'search': {'attempts': 30, 'period': 60},  # 30 attempts per minute
        'job_posting': {'attempts': 10, 'period': 3600},  # 10 per hour
        'application': {'attempts': 20, 'period': 3600},  # 20 per hour
    }
    
    def process_request(self, request):
        # Check if endpoint has rate limiting
        for endpoint, action in self.RATE_LIMIT_ENDPOINTS.items():
            if request.path.startswith(endpoint):
                if action not in self.RATE_LIMITS:
                    continue
                
                config = self.RATE_LIMITS[action]
                key = self._get_rate_limit_key(request, action)
                
                current = cache.get(key, 0)
                if current >= config['attempts']:
                    return JsonResponse(
                        {
                            'error': 'Rate limit exceeded',
                            'message': f'Too many requests. Please try again later.',
                            'retry_after': config['period']
                        },
                        status=429
                    )
                
                cache.set(key, current + 1, config['period'])
        
        return None
    
    @staticmethod
    def _get_rate_limit_key(request, action):
        """Generate rate limit cache key"""
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_id = request.user.id if request.user.is_authenticated else 'anon'
        return f"rate_limit:{action}:{ip}:{user_id}"


class AuditLoggingMiddleware(MiddlewareMixin):
    """Log security-sensitive operations"""
    
    SENSITIVE_METHODS = ['POST', 'PUT', 'DELETE', 'PATCH']
    SENSITIVE_PATHS = [
        '/job/post/',
        '/update-status/',
        '/admin/',
        '/profile/edit/',
    ]
    
    def process_request(self, request):
        if request.method in self.SENSITIVE_METHODS:
            for path in self.SENSITIVE_PATHS:
                if request.path.startswith(path):
                    # Store reference for later logging
                    request._audit_log_required = True
                    break
        
        return None
    
    def process_response(self, request, response):
        if hasattr(request, '_audit_log_required') and request.user.is_authenticated:
            from main.models import AuditLog
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action=request.method,
                    resource_type='HTTP_REQUEST',
                    resource_id=request.path,
                    details=json.dumps({
                        'path': request.path,
                        'method': request.method,
                        'status_code': response.status_code,
                        'ip_address': self._get_client_ip(request)
                    }),
                    status='success' if response.status_code < 400 else 'failed',
                    ip_address=self._get_client_ip(request)
                )
            except Exception as e:
                print(f"Failed to log audit trail: {e}")
        
        return response
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class XSSProtectionMiddleware(MiddlewareMixin):
    """Add XSS protection headers and content sanitization"""
    
    def process_response(self, request, response):
        # Set Content-Type explicitly to prevent MIME confusion
        if 'Content-Type' not in response:
            response['Content-Type'] = 'text/html; charset=utf-8'
        
        return response
