from rest_framework import permissions
import fnmatch
import logging

logger = logging.getLogger('subscriptions')


class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and \
            (hasattr(request.user, 'role') and int(request.user.role) == 1)
    

class IsRestaurantOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and \
            (hasattr(request.user, 'role') and int(request.user.role) == 2)

class IsDriver(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and \
            (hasattr(request.user, 'role') and int(request.user.role) == 3)


class HasSubscriptionFeature(permissions.BasePermission):
    """
    Permission class to check if user has access to a feature based on subscription.
    Only applies to restaurant owners. Other roles bypass this check.
    """
    message = 'Your subscription plan does not include access to this feature. Please upgrade your plan.'
    
    def has_permission(self, request, view):
        """
        Check if user has subscription access to the requested feature/endpoint.
        
        Args:
            request: HTTP request
            view: View being accessed
            
        Returns:
            bool: True if user has access, False otherwise
        """
        # Allow non-authenticated requests to pass (will be caught by other permissions)
        if not request.user.is_authenticated:
            return True
        
        # Only check subscription for restaurant owners
        if not hasattr(request.user, 'role') or request.user.role != 2:
            return True
        
        # Check if user has an active subscription
        if not hasattr(request.user, 'subscription'):
            logger.warning(f"Restaurant owner {request.user.id} has no subscription")
            return False
        
        subscription = request.user.subscription
        
        # Check if subscription is expired (and not in grace period)
        if subscription.is_expired() and not subscription.in_grace_period():
            logger.info(f"User {request.user.id} subscription is expired")
            return False
        
        # Get the URL path being accessed
        url_path = request.path_info.strip('/')
        
        # Remove API version prefix if present (e.g., 'api/v1/')
        if url_path.startswith('api/'):
            parts = url_path.split('/', 2)
            if len(parts) > 2:
                url_path = parts[2]
        
        # Check if user has access to this URL
        has_access = subscription.has_url_access(url_path)
        
        if not has_access:
            logger.info(
                f"User {request.user.id} denied access to {url_path} - "
                f"not included in {subscription.plan.name} plan"
            )
        
        return has_access


def require_subscription_feature(feature_name):
    """
    Decorator to require a specific subscription feature.
    
    Usage:
        @require_subscription_feature('pos_ordering')
        def my_view(request):
            ...
    
    Args:
        feature_name (str): Name of the required feature
        
    Returns:
        function: Decorated view function
    """
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            # Allow non-authenticated requests to pass
            if not request.user.is_authenticated:
                from rest_framework.exceptions import NotAuthenticated
                raise NotAuthenticated()
            
            # Only check for restaurant owners
            if hasattr(request.user, 'role') and request.user.role == 2:
                if not hasattr(request.user, 'subscription'):
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('No active subscription found.')
                
                subscription = request.user.subscription
                
                # Check if expired (and not in grace period)
                if subscription.is_expired() and not subscription.in_grace_period():
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('Your subscription has expired.')
                
                # Check if user has the required feature
                if not subscription.has_feature(feature_name):
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied(
                        f'Your subscription plan does not include the {feature_name} feature. '
                        f'Please upgrade your plan.'
                    )
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator
