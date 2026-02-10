"""Platform revenue analytics.

Revenue statistics, payment breakdowns, and financial metrics.
"""

from datetime import datetime
from typing import Dict, Optional, Any

from django.db.models import (
    Count, Sum, Avg, Max, Min, Case, When
)
from django.core.cache import cache

from order.models import Order
from payment.models import Payment


def get_platform_revenue_stats(
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    order_source: Optional[int] = None
) -> Dict[str, Any]:
    """Get platform-wide revenue statistics.
    
    Args:
        date_start: Start date for filtering (inclusive).
        date_end: End date for filtering (inclusive).
        order_source: Filter by order source (1=Online, 2=POS).
        
    Returns:
        Dictionary containing revenue metrics including total revenue,
        order count, average order value, payment method breakdown,
        and order status distribution.
    """
    cache_key = f"platform_revenue_stats_{date_start}_{date_end}_{order_source}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    queryset = Order.objects.filter(is_active=True)
    
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    if order_source:
        queryset = queryset.filter(order_source=order_source)
    
    # Aggregate stats
    stats = queryset.aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('total_price'),
        avg_order_value=Avg('total_price'),
        max_order_value=Max('total_price'),
        min_order_value=Min('total_price'),
        
        # Order status breakdown
        pending=Count(Case(When(status=1, then=1))),
        preparing=Count(Case(When(status=2, then=1))),
        ready_for_pickup=Count(Case(When(status=3, then=1))),
        out_for_delivery=Count(Case(When(status=4, then=1))),
        delivered=Count(Case(When(status=5, then=1))),
        cancelled=Count(Case(When(status=6, then=1))),
        completed=Count(Case(When(status=7, then=1))),
        
        # Order source breakdown
        online_orders=Count(Case(When(order_source=1, then=1))),
        pos_orders=Count(Case(When(order_source=2, then=1))),
    )
    
    # Payment method breakdown
    payment_breakdown = Payment.objects.filter(
        order__in=queryset
    ).values('method').annotate(
        count=Count('id'),
        total_amount=Sum('amount')
    ).order_by('-count')
    
    # Convert to dictionary with method names
    payment_method_map = {
        1: 'Cash on Delivery',
        2: 'Stripe',
        3: 'Cash',
        4: 'MFS',
        5: 'Card',
        9: 'Other'
    }
    
    stats['payment_methods'] = [
        {
            'method': payment_method_map.get(item['method'], 'Unknown'),
            'method_id': item['method'],
            'count': item['count'],
            'total_amount': float(item['total_amount'] or 0)
        }
        for item in payment_breakdown
    ]
    
    # Calculate conversion metrics
    total_orders = stats['total_orders'] or 1  # Prevent division by zero
    stats['completion_rate'] = round(
        ((stats['delivered'] + stats['completed']) / total_orders) * 100, 2
    )
    stats['cancellation_rate'] = round((stats['cancelled'] / total_orders) * 100, 2)
    
    # Format currency values
    stats['total_revenue'] = float(stats['total_revenue'] or 0)
    stats['avg_order_value'] = float(stats['avg_order_value'] or 0)
    stats['max_order_value'] = float(stats['max_order_value'] or 0)
    stats['min_order_value'] = float(stats['min_order_value'] or 0)
    
    # Cache for 30 minutes
    cache.set(cache_key, stats, 1800)
    
    return stats
