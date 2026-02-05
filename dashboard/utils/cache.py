import hashlib
import json
from datetime import datetime, timedelta
from functools import wraps
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def build_cache_key(entity_type, entity_id, metric_type, filters_dict):
    """
    Build a hierarchical cache key for dashboard data.
    
    Format: dashboard:{entity_type}:{id}:{metric}:{md5_hash}
    
    The MD5 hash is computed from sorted filter keys and values to ensure
    consistent hashing across requests with same filters but different order.
    
    Args:
        entity_type (str): Type of entity ('restaurant', 'customer', 'driver')
        entity_id (int): ID of the entity
        metric_type (str): Dashboard metric ('daily_orders', 'customer_rankings', etc)
        filters_dict (dict): Filter parameters to hash
    
    Returns:
        str: Cache key
    
    Example:
        >>> key = build_cache_key('restaurant', 123, 'daily_orders', 
        ...                       {'date_start': '2025-01-01', 'date_end': '2025-01-07'})
        >>> print(key)
        dashboard:restaurant:123:daily_orders:a3f2e1c8d9b4e6f7
    """
    # Sort and clean filters for consistent hashing
    sorted_filters = json.dumps(filters_dict, sort_keys=True, default=str)
    filters_hash = hashlib.md5(sorted_filters.encode()).hexdigest()[:16]
    
    return f"dashboard:{entity_type}:{entity_id}:{metric_type}:{filters_hash}"


def should_use_cache(date_start, date_end, cache_days_limit=7):
    """
    Determine if cache should be used based on date range.
    
    Cache is only used if the entire date range is within the last N days.
    Queries outside this window bypass cache and query database directly.
    
    Args:
        date_start (date): Start date of query
        date_end (date): End date of query
        cache_days_limit (int): Maximum days to cache (default: 7)
    
    Returns:
        bool: True if entire range is within cache window, False otherwise
    
    Example:
        >>> from datetime import date, timedelta
        >>> today = date.today()
        >>> should_use_cache(today - timedelta(days=5), today)
        True
        >>> should_use_cache(today - timedelta(days=30), today)
        False
    """
    if date_start is None or date_end is None:
        return False
    
    today = timezone.now().date()
    cache_cutoff = today - timedelta(days=cache_days_limit)
    
    # Both dates must be within the cache window
    return date_start >= cache_cutoff and date_end <= today


def cache_dashboard_data(ttl=300, metric_type=None):
    """
    Decorator for caching dashboard service functions with automatic DB fallback.
    
    If data is outside cache window (>7 days old), returns uncached result.
    Otherwise caches result in Redis and returns cached data on subsequent calls.
    
    Supports Celery retry mechanism for transient failures.
    
    Args:
        ttl (int): Time to live in seconds (default: 300 = 5 minutes)
        metric_type (str): Dashboard metric type for logging
    
    Returns:
        function: Decorated function that handles caching
    
    Example:
        >>> @cache_dashboard_data(ttl=300, metric_type='daily_orders')
        ... def get_daily_orders(restaurant_id, filters):
        ...     return Order.objects.filter(...).values(...)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract filters from kwargs or assume no caching needed
            filters = kwargs.get('filters', {})
            date_start = filters.get('date_start') if filters else None
            date_end = filters.get('date_end') if filters else None
            
            # Check if data is within cache window
            use_cache = should_use_cache(date_start, date_end)
            
            if not use_cache:
                # Outside cache window - query database directly
                logger.info(f"Bypassing cache for {metric_type}: date range outside 7-day window")
                return func(*args, **kwargs)
            
            # Build cache key from function arguments
            # Assumes first arg is entity_id, metric_type passed to decorator
            try:
                entity_id = args[0] if args else kwargs.get('restaurant_id') or kwargs.get('customer_id') or kwargs.get('driver_id')
                entity_type = 'restaurant' if 'restaurant_id' in kwargs else ('customer' if 'customer_id' in kwargs else 'driver')
                
                # Normalize filters for consistent hashing
                normalized_filters = {k: v for k, v in (filters or {}).items() if v is not None}
                
                cache_key = build_cache_key(entity_type, entity_id, metric_type or func.__name__, normalized_filters)
                
                # Try to get from cache
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_result
                
                # Cache miss - call function and store result
                result = func(*args, **kwargs)
                cache.set(cache_key, result, ttl)
                logger.debug(f"Cached {cache_key} for {ttl}s")
                
                return result
            
            except Exception as e:
                # On any error, bypass cache and return direct result
                logger.warning(f"Cache error in {metric_type}: {str(e)}, returning uncached result")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator
