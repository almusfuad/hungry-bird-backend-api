"""Growth rate analytics.

Period-over-period growth rate calculations and comparisons.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from django.core.cache import cache
from django.db.models import Count, Sum, Avg, Q, Case, When
from django.utils import timezone

from order.models import Order


def calculate_growth_rate(
    restaurant_id: Optional[int] = None,
    comparison_type: str = 'mom',  # 'mom', 'wow', 'yoy'
    current_period_start: Optional[datetime] = None,
    current_period_end: Optional[datetime] = None
) -> Dict[str, Any]:
    """Calculate period-over-period growth rates.
    
    Args:
        restaurant_id: Restaurant ID for restaurant-specific metrics.
                      If None, calculates platform-wide growth.
        comparison_type: Type of comparison - 'mom' (month-over-month),
                        'wow' (week-over-week), or 'yoy' (year-over-year).
        current_period_start: Start of current period.
        current_period_end: End of current period.
        
    Returns:
        Dictionary containing current and previous period metrics
        with growth rate calculations.
    """
    cache_key = f"growth_rate_{restaurant_id}_{comparison_type}_{current_period_start}_{current_period_end}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # Determine time delta for comparison
    if not current_period_end:
        current_period_end = timezone.now()
    
    if comparison_type == 'mom':
        delta = timedelta(days=30)
        period_name = 'Month-over-Month'
    elif comparison_type == 'wow':
        delta = timedelta(days=7)
        period_name = 'Week-over-Week'
    elif comparison_type == 'yoy':
        delta = timedelta(days=365)
        period_name = 'Year-over-Year'
    else:
        delta = timedelta(days=30)
        period_name = 'Month-over-Month'
    
    if not current_period_start:
        current_period_start = current_period_end - delta
    
    # Calculate period length
    period_length = (current_period_end - current_period_start).days
    previous_period_end = current_period_start
    previous_period_start = previous_period_end - timedelta(days=period_length)
    
    # Get current period metrics
    current_metrics = _get_period_metrics(
        restaurant_id,
        current_period_start,
        current_period_end
    )
    
    # Get previous period metrics
    previous_metrics = _get_period_metrics(
        restaurant_id,
        previous_period_start,
        previous_period_end
    )
    
    # Calculate growth rates
    def calc_growth(current: float, previous: float) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)
    
    result = {
        'comparison_type': comparison_type,
        'period_name': period_name,
        'current_period': {
            'start': current_period_start.isoformat(),
            'end': current_period_end.isoformat(),
            **current_metrics
        },
        'previous_period': {
            'start': previous_period_start.isoformat(),
            'end': previous_period_end.isoformat(),
            **previous_metrics
        },
        'growth_rates': {
            'revenue_growth': calc_growth(
                current_metrics['revenue'],
                previous_metrics['revenue']
            ),
            'order_growth': calc_growth(
                current_metrics['order_count'],
                previous_metrics['order_count']
            ),
            'customer_growth': calc_growth(
                current_metrics['unique_customers'],
                previous_metrics['unique_customers']
            ),
            'avg_order_value_growth': calc_growth(
                current_metrics['avg_order_value'],
                previous_metrics['avg_order_value']
            ),
        }
    }
    
    # Cache for 30 minutes
    cache.set(cache_key, result, 1800)
    
    return result


def _get_period_metrics(
    restaurant_id: Optional[int],
    period_start: datetime,
    period_end: datetime
) -> Dict[str, float]:
    """Get metrics for a specific time period.
    
    Args:
        restaurant_id: Restaurant ID or None for platform-wide.
        period_start: Start of period.
        period_end: End of period.
        
    Returns:
        Dictionary containing period metrics.
    """
    queryset = Order.objects.filter(
        is_active=True,
        created_at__gte=period_start,
        created_at__lte=period_end
    )
    
    if restaurant_id:
        queryset = queryset.filter(restaurant_id=restaurant_id)
    
    metrics = queryset.aggregate(
        revenue=Sum('total_price'),
        order_count=Count('id'),
        avg_order_value=Avg('total_price'),
        unique_customers=Count('customer', distinct=True),
        completed=Count(Case(When(Q(status=5) | Q(status=7), then=1))),
    )
    
    return {
        'revenue': float(metrics['revenue'] or 0),
        'order_count': metrics['order_count'] or 0,
        'avg_order_value': float(metrics['avg_order_value'] or 0),
        'unique_customers': metrics['unique_customers'] or 0,
        'completed_orders': metrics['completed'] or 0,
    }
