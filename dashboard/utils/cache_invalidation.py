from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def invalidate_metric_cache(entity_type, entity_id, metric_type):
    """
    Invalidate specific metric cache for an entity.
    
    Uses Redis pattern deletion to remove all cached variations of a metric
    (different filter combinations) in a single operation.
    
    Args:
        entity_type (str): Type of entity ('restaurant', 'customer', 'driver')
        entity_id (int): ID of the entity
        metric_type (str): Specific metric to invalidate (e.g., 'daily_orders')
    
    Example:
        >>> invalidate_metric_cache('restaurant', 123, 'daily_orders')
        # Deletes all cache keys matching: dashboard:restaurant:123:daily_orders:*
    """
    pattern = f"dashboard:{entity_type}:{entity_id}:{metric_type}:*"
    
    try:
        # Get cache backend and delete pattern
        cache_backend = cache._cache
        
        # For Redis backend, use delete_pattern
        if hasattr(cache_backend, 'delete_pattern'):
            cache_backend.delete_pattern(pattern)
            logger.info(f"Invalidated cache pattern: {pattern}")
        else:
            # Fallback: manually delete known keys (less efficient)
            logger.warning(f"Cache backend doesn't support pattern deletion for {pattern}")
    
    except Exception as e:
        logger.error(f"Error invalidating cache for {pattern}: {str(e)}")


def invalidate_entity_cache(entity_type, entity_id, metric_types=None):
    """
    Invalidate all cached data for an entity.
    
    If metric_types specified, only invalidates those metrics.
    Otherwise invalidates all metrics for the entity.
    
    Args:
        entity_type (str): Type of entity ('restaurant', 'customer', 'driver')
        entity_id (int): ID of the entity
        metric_types (list, optional): Specific metrics to invalidate
                                      If None, invalidates all metrics
    
    Example:
        >>> # Invalidate only daily_orders
        >>> invalidate_entity_cache('restaurant', 123, ['daily_orders', 'popular_items'])
        
        >>> # Invalidate all metrics for restaurant
        >>> invalidate_entity_cache('restaurant', 123)
    """
    if metric_types is None:
        # Invalidate all metrics
        pattern = f"dashboard:{entity_type}:{entity_id}:*"
    else:
        # Invalidate specific metrics
        for metric_type in metric_types:
            invalidate_metric_cache(entity_type, entity_id, metric_type)
        return
    
    try:
        cache_backend = cache._cache
        if hasattr(cache_backend, 'delete_pattern'):
            cache_backend.delete_pattern(pattern)
            logger.info(f"Invalidated all cache for: {pattern}")
        else:
            logger.warning(f"Cache backend doesn't support pattern deletion for {pattern}")
    
    except Exception as e:
        logger.error(f"Error invalidating cache for {pattern}: {str(e)}")


def invalidate_on_order_change(order):
    """
    Invalidate all affected caches when an order changes.
    
    Called when order is created/updated/deleted. Invalidates metrics
    that depend on this order's data.
    
    Args:
        order: Order instance that changed
    """
    # Invalidate restaurant metrics
    invalidate_metric_cache('restaurant', order.restaurant_id, 'daily_orders')
    invalidate_metric_cache('restaurant', order.restaurant_id, 'order_source')
    invalidate_metric_cache('restaurant', order.restaurant_id, 'customer_rankings')
    
    # Invalidate customer metrics
    invalidate_metric_cache('customer', order.customer_id, 'customer_overview')
    
    # Invalidate driver metrics if driver assigned
    if order.driver_id:
        invalidate_metric_cache('restaurant', order.restaurant_id, 'driver_performance')
        invalidate_metric_cache('driver', order.driver_id, 'driver_overview')
    
    logger.info(f"Invalidated caches for order {order.id}")


def invalidate_on_order_item_change(order_item):
    """
    Invalidate all affected caches when an order item changes.
    
    Called when order item is created/updated/deleted. Invalidates metrics
    that depend on menu item ordering data.
    
    Args:
        order_item: OrderItem instance that changed
    """
    order = order_item.order
    restaurant_id = order_item.menu_item.restaurant_id
    
    # Invalidate popular items metric
    invalidate_metric_cache('restaurant', restaurant_id, 'popular_items')
    
    logger.info(f"Invalidated popular_items cache for restaurant {restaurant_id}")


def invalidate_on_payment_change(payment):
    """
    Invalidate all affected caches when a payment changes.
    
    Called when payment is created/updated. Invalidates metrics that depend
    on payment method data.
    
    Args:
        payment: Payment instance that changed
    """
    order = payment.order
    
    # Invalidate order source metrics (includes payment breakdown)
    invalidate_metric_cache('restaurant', order.restaurant_id, 'order_source')
    
    logger.info(f"Invalidated order_source cache for order {order.id}")
