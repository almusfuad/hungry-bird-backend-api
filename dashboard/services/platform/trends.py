"""Platform order trends analytics.

Time-series analysis of orders, revenue, and customer engagement.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from django.db.models import (
    Count, Sum, Avg, Q, Case, When
)
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncHour
from django.core.cache import cache

from order.models import Order


def get_order_trends(
    grouping: str = 'daily',
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """Get order volume and revenue trends over time.
    
    Args:
        grouping: Time grouping - 'hourly', 'daily', 'weekly', or 'monthly'.
        date_start: Start date for filtering (inclusive).
        date_end: End date for filtering (inclusive).
        limit: Maximum number of time periods to return.
        
    Returns:
        List of dictionaries with trend data grouped by time period.
    """
    cache_key = f"order_trends_{grouping}_{date_start}_{date_end}_{limit}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    queryset = Order.objects.filter(is_active=True)
    
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    
    # Select truncation function based on grouping
    trunc_map = {
        'hourly': TruncHour,
        'daily': TruncDate,
        'weekly': TruncWeek,
        'monthly': TruncMonth,
    }
    
    trunc_func = trunc_map.get(grouping, TruncDate)
    
    results = queryset.annotate(
        period=trunc_func('created_at')
    ).values('period').annotate(
        total_orders=Count('id'),
        revenue=Sum('total_price'),
        avg_order_value=Avg('total_price'),
        
        # Order source breakdown
        online_orders=Count(Case(When(order_source=1, then=1))),
        pos_orders=Count(Case(When(order_source=2, then=1))),
        
        # Status breakdown
        completed=Count(Case(When(Q(status=5) | Q(status=7), then=1))),
        cancelled=Count(Case(When(status=6, then=1))),
        
        # Customer metrics
        unique_customers=Count('customer', distinct=True),
        unique_restaurants=Count('restaurant', distinct=True),
    ).order_by('-period')[:limit]
    
    # Format results
    trends = []
    for item in results:
        trends.append({
            'period': item['period'].isoformat() if item['period'] else None,
            'total_orders': item['total_orders'],
            'revenue': float(item['revenue'] or 0),
            'avg_order_value': float(item['avg_order_value'] or 0),
            'online_orders': item['online_orders'],
            'pos_orders': item['pos_orders'],
            'completed': item['completed'],
            'cancelled': item['cancelled'],
            'unique_customers': item['unique_customers'],
            'unique_restaurants': item['unique_restaurants'],
            'completion_rate': round(
                (item['completed'] / item['total_orders'] * 100) if item['total_orders'] > 0 else 0,
                2
            ),
        })
    
    # Cache for 30 minutes
    cache.set(cache_key, trends, 1800)
    
    return trends
