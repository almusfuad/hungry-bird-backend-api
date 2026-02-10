"""Platform rankings and leaderboards.

Top performing restaurants, trending items, and customer metrics.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from django.db.models import (
    Count, Sum, Avg, F, Q, Case, When,
    DecimalField
)
from django.core.cache import cache
from django.utils import timezone

from order.models import OrderItem
from restaurant.models import Restaurant, MenuItem
from authUser.models import User


def get_trending_items(
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get trending menu items across all restaurants.
    
    Args:
        date_start: Start date for filtering (inclusive).
        date_end: End date for filtering (inclusive).
        limit: Maximum number of items to return.
        
    Returns:
        List of trending menu items with order counts, revenue,
        ratings, and trend indicators.
    """
    cache_key = f"trending_items_{date_start}_{date_end}_{limit}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # Base order filter
    order_filter = Q(orderitem__order__is_active=True)
    if date_start:
        order_filter &= Q(orderitem__order__created_at__gte=date_start)
    if date_end:
        order_filter &= Q(orderitem__order__created_at__lte=date_end)
    
    # Calculate trending score with recency weight
    now = timezone.now()
    days_in_period = 30
    if date_start:
        days_in_period = (now - date_start).days or 1
    
    results = MenuItem.objects.filter(
        is_active=True,
        orderitem__order__is_active=True
    ).annotate(
        times_ordered=Count('orderitem__order', distinct=True, filter=order_filter),
        total_quantity=Sum('orderitem__quantity', filter=order_filter),
        total_revenue=Sum(
            F('orderitem__quantity') * F('price'),
            output_field=DecimalField(),
            filter=order_filter
        ),
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_active=True, reviews__menu_item__isnull=False)),
        review_count=Count('reviews', filter=Q(reviews__is_active=True, reviews__menu_item__isnull=False)),
        unique_customers=Count('orderitem__order__customer', distinct=True, filter=order_filter),
        
        # Calculate velocity (orders per day)
        velocity=Count('orderitem__order', distinct=True, filter=order_filter) / days_in_period,
    ).filter(
        times_ordered__gt=0
    ).order_by('-velocity', '-times_ordered')[:limit]
    
    trending = []
    for item in results:
        trending.append({
            'id': item.id,
            'name': item.name,
            'category': item.get_category_display(),
            'category_id': item.category,
            'price': float(item.price),
            'restaurant_id': item.restaurant_id,
            'restaurant_name': item.restaurant.name if item.restaurant else None,
            'times_ordered': item.times_ordered,
            'total_quantity': item.total_quantity or 0,
            'total_revenue': float(item.total_revenue or 0),
            'avg_rating': float(item.avg_rating or 0),
            'review_count': item.review_count,
            'unique_customers': item.unique_customers,
            'velocity': round(float(item.velocity or 0), 2),
            'image': item.image.url if item.image else None,
        })
    
    # Cache for 30 minutes
    cache.set(cache_key, trending, 1800)
    
    return trending


def get_top_restaurants(
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get top performing restaurants by revenue and orders.
    
    Args:
        date_start: Start date for filtering (inclusive).
        date_end: End date for filtering (inclusive).
        limit: Maximum number of restaurants to return.
        
    Returns:
        List of top restaurants with performance metrics.
    """
    cache_key = f"top_restaurants_{date_start}_{date_end}_{limit}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    order_filter = Q(orders__is_active=True)
    if date_start:
        order_filter &= Q(orders__created_at__gte=date_start)
    if date_end:
        order_filter &= Q(orders__created_at__lte=date_end)
    
    results = Restaurant.objects.filter(
        is_active=True
    ).annotate(
        total_orders=Count('orders', filter=order_filter),
        total_revenue=Sum('orders__total_price', filter=order_filter),
        avg_order_value=Avg('orders__total_price', filter=order_filter),
        completed_orders=Count(
            'orders',
            filter=order_filter & Q(orders__status__in=[5, 7])
        ),
        cancelled_orders=Count(
            'orders',
            filter=order_filter & Q(orders__status=6)
        ),
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_active=True, reviews__menu_item__isnull=True)),
        review_count=Count('reviews', filter=Q(reviews__is_active=True, reviews__menu_item__isnull=True)),
        unique_customers=Count('orders__customer', distinct=True, filter=order_filter),
    ).filter(
        total_orders__gt=0
    ).order_by('-total_revenue')[:limit]
    
    top_restaurants = []
    for restaurant in results:
        total_orders = restaurant.total_orders or 1
        top_restaurants.append({
            'id': restaurant.id,
            'name': restaurant.name,
            'owner_name': restaurant.owner.get_full_name() if restaurant.owner else None,
            'total_orders': restaurant.total_orders,
            'total_revenue': float(restaurant.total_revenue or 0),
            'avg_order_value': float(restaurant.avg_order_value or 0),
            'completed_orders': restaurant.completed_orders,
            'cancelled_orders': restaurant.cancelled_orders,
            'completion_rate': round((restaurant.completed_orders / total_orders) * 100, 2),
            'cancellation_rate': round((restaurant.cancelled_orders / total_orders) * 100, 2),
            'avg_rating': float(restaurant.avg_rating or 0),
            'review_count': restaurant.review_count,
            'unique_customers': restaurant.unique_customers,
            'image': restaurant.image.url if restaurant.image else None,
        })
    
    # Cache for 30 minutes
    cache.set(cache_key, top_restaurants, 1800)
    
    return top_restaurants


def get_customer_metrics(
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get platform-wide customer metrics.
    
    Args:
        date_start: Start date for filtering (inclusive).
        date_end: End date for filtering (inclusive).
        
    Returns:
        Dictionary containing customer acquisition, retention,
        and engagement metrics.
    """
    cache_key = f"customer_metrics_{date_start}_{date_end}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    order_filter = Q(orders__is_active=True)
    if date_start:
        order_filter &= Q(orders__created_at__gte=date_start)
    if date_end:
        order_filter &= Q(orders__created_at__lte=date_end)
    
    # Total customers
    total_customers = User.objects.filter(role=1, is_active=True).count()
    
    # Active customers (placed at least one order)
    active_customers = User.objects.filter(
        role=1,
        is_active=True,
        orders__is_active=True
    )
    
    if date_start:
        active_customers = active_customers.filter(orders__created_at__gte=date_start)
    if date_end:
        active_customers = active_customers.filter(orders__created_at__lte=date_end)
    
    active_customers = active_customers.distinct().count()
    
    # Customer segmentation by order count
    customer_segments = User.objects.filter(
        role=1,
        is_active=True
    ).annotate(
        order_count=Count('orders', filter=order_filter),
        total_spent=Sum('orders__total_price', filter=order_filter),
        avg_order_value=Avg('orders__total_price', filter=order_filter),
    ).aggregate(
        new_customers=Count(Case(When(order_count=0, then=1))),
        one_time_buyers=Count(Case(When(order_count=1, then=1))),
        repeat_customers=Count(Case(When(order_count__gte=2, order_count__lt=5, then=1))),
        loyal_customers=Count(Case(When(order_count__gte=5, then=1))),
        avg_customer_lifetime_value=Avg('total_spent'),
    )
    
    metrics = {
        'total_customers': total_customers,
        'active_customers': active_customers,
        'new_customers': customer_segments['new_customers'] or 0,
        'one_time_buyers': customer_segments['one_time_buyers'] or 0,
        'repeat_customers': customer_segments['repeat_customers'] or 0,
        'loyal_customers': customer_segments['loyal_customers'] or 0,
        'avg_customer_lifetime_value': float(customer_segments['avg_customer_lifetime_value'] or 0),
        'customer_retention_rate': round(
            ((customer_segments['repeat_customers'] + customer_segments['loyal_customers']) / 
             (active_customers or 1)) * 100,
            2
        ),
    }
    
    # Cache for 30 minutes
    cache.set(cache_key, metrics, 1800)
    
    return metrics
