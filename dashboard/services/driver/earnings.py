"""Driver earnings breakdown.

Time-based earnings analysis and revenue tracking.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from django.core.cache import cache
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth

from order.models import Order


def get_driver_earnings_breakdown(
    driver_id: int,
    grouping: str = 'daily',
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """Get driver earnings breakdown over time.
    
    Args:
        driver_id: Driver user ID.
        grouping: Time grouping - 'daily', 'weekly', or 'monthly'.
        date_start: Start date for filtering (inclusive).
        date_end: End date for filtering (inclusive).
        limit: Maximum number of periods to return.
        
    Returns:
        List of earnings data grouped by time period.
    """
    cache_key = f"driver_earnings_{driver_id}_{grouping}_{date_start}_{date_end}_{limit}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    queryset = Order.objects.filter(
        driver_id=driver_id,
        status__in=[5, 7],
        is_active=True
    )
    
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    
    # Select truncation function
    trunc_map = {
        'daily': TruncDate,
        'weekly': TruncWeek,
        'monthly': TruncMonth,
    }
    
    trunc_func = trunc_map.get(grouping, TruncDate)
    
    results = queryset.annotate(
        period=trunc_func('created_at')
    ).values('period').annotate(
        total_deliveries=Count('id'),
        total_earnings=Sum('total_price'),
        avg_earnings_per_delivery=Avg('total_price'),
    ).order_by('-period')[:limit]
    
    earnings_data = [
        {
            'period': item['period'].isoformat() if item['period'] else None,
            'total_deliveries': item['total_deliveries'],
            'total_earnings': float(item['total_earnings'] or 0),
            'avg_earnings_per_delivery': float(item['avg_earnings_per_delivery'] or 0),
        }
        for item in results
    ]
    
    # Cache for 30 minutes
    cache.set(cache_key, earnings_data, 1800)
    
    return earnings_data
