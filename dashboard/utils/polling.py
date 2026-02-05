from dashboard.models import POLLING_INTERVALS
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def get_polling_response(data, user_role, cached_at=None, was_cached=False):
    """
    Format dashboard data response with polling metadata.
    
    Includes cache information and polling interval recommendations based on user role.
    
    Args:
        data (dict or list): Dashboard data to return
        user_role (int): User role (1=Customer, 2=Owner, 3=Driver)
        cached_at (datetime, optional): When data was cached/fetched
        was_cached (bool): Whether result came from cache
    
    Returns:
        dict: Response with data, cache metadata, and polling interval
    
    Example:
        >>> response = get_polling_response(
        ...     data=daily_orders_data,
        ...     user_role=2,
        ...     cached_at=timezone.now(),
        ...     was_cached=True
        ... )
        >>> print(response['next_poll_seconds'])
        300
    """
    
    # Determine user role name and polling interval
    role_name_map = {1: 'CUSTOMER', 2: 'RESTAURANT', 3: 'DRIVER'}
    role_name = role_name_map.get(user_role, 'CUSTOMER')
    next_poll_seconds = POLLING_INTERVALS.get(role_name, 900)
    
    # Use current time if not provided
    if cached_at is None:
        cached_at = timezone.now()
    
    return {
        'data': data,
        'cached_at': cached_at.isoformat() if hasattr(cached_at, 'isoformat') else str(cached_at),
        'was_cached': was_cached,
        'next_poll_seconds': next_poll_seconds,
        'next_poll_minutes': round(next_poll_seconds / 60, 1),
        'server_time': timezone.now().isoformat(),
    }
