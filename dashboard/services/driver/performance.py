"""Driver performance ranking and history.

Driver rankings, performance tracking, and historical analysis.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from django.core.cache import cache
from django.db.models import Count, Sum, Q
from django.utils import timezone

from authUser.models import User
from .efficiency import get_driver_efficiency_metrics
from .earnings import get_driver_earnings_breakdown


def get_driver_performance_ranking(
    restaurant_id: Optional[int] = None,
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get ranked list of drivers by performance metrics.
    
    Args:
        restaurant_id: Optional restaurant ID to filter drivers.
        date_start: Start date for filtering (inclusive).
        date_end: End date for filtering (inclusive).
        limit: Maximum number of drivers to return.
        
    Returns:
        List of drivers ranked by performance score.
    """
    cache_key = f"driver_ranking_{restaurant_id}_{date_start}_{date_end}_{limit}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # Base driver queryset
    drivers = User.objects.filter(role=3, is_active=True)
    
    if restaurant_id:
        drivers = drivers.filter(restaurants__id=restaurant_id)
    
    # Get order metrics for each driver
    order_filter = Q(driver__role=3, is_active=True, status__in=[5, 7])
    if date_start:
        order_filter &= Q(created_at__gte=date_start)
    if date_end:
        order_filter &= Q(created_at__lte=date_end)
    
    driver_stats = drivers.annotate(
        total_deliveries=Count('driver_orders', filter=order_filter),
        total_earnings=Sum('driver_orders__total_price', filter=order_filter),
    ).filter(
        total_deliveries__gt=0
    )
    
    # Calculate performance scores for ranking
    rankings = []
    for driver in driver_stats:
        # Calculate detailed metrics
        efficiency_metrics = get_driver_efficiency_metrics(
            driver.id,
            date_start,
            date_end
        )
        
        # Performance score (weighted combination)
        # Formula: 50% deliveries + 30% on-time rate + 20% acceptance rate
        # (Note: No rating component as there's no driver review system yet)
        performance_score = (
            (efficiency_metrics['completed_deliveries'] * 0.5) +
            (efficiency_metrics['on_time_delivery_rate'] * 0.3) +
            (efficiency_metrics['acceptance_rate'] * 0.2)
        )
        
        rankings.append({
            'driver_id': driver.id,
            'driver_name': driver.get_full_name(),
            'total_deliveries': efficiency_metrics['completed_deliveries'],
            'total_earnings': float(driver.total_earnings or 0),
            'avg_rating': efficiency_metrics['avg_rating'],
            'review_count': 0,  # No driver reviews yet
            'acceptance_rate': efficiency_metrics['acceptance_rate'],
            'on_time_delivery_rate': efficiency_metrics['on_time_delivery_rate'],
            'avg_delivery_time_minutes': efficiency_metrics['avg_delivery_time_minutes'],
            'performance_score': round(performance_score, 2),
        })
    
    # Sort by performance score
    rankings.sort(key=lambda x: x['performance_score'], reverse=True)
    
    # Add rank position
    for idx, driver_data in enumerate(rankings[:limit], start=1):
        driver_data['rank'] = idx
    
    result = rankings[:limit]
    
    # Cache for 30 minutes
    cache.set(cache_key, result, 1800)
    
    return result


def get_driver_performance_history(
    driver_id: int,
    grouping: str = 'weekly',
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
    limit: int = 12
) -> List[Dict[str, Any]]:
    """Get driver performance metrics over time.
    
    Args:
        driver_id: Driver user ID.
        grouping: Time grouping - 'daily', 'weekly', or 'monthly'.
        date_start: Start date for filtering (inclusive).
        date_end: End date for filtering (inclusive).
        limit: Maximum number of periods to return.
        
    Returns:
        List of performance metrics grouped by time period.
    """
    cache_key = f"driver_performance_history_{driver_id}_{grouping}_{date_start}_{date_end}_{limit}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    if not date_end:
        date_end = timezone.now()
    
    # Calculate period duration
    if grouping == 'daily':
        period_days = 1
        total_periods = limit
    elif grouping == 'weekly':
        period_days = 7
        total_periods = limit
    elif grouping == 'monthly':
        period_days = 30
        total_periods = limit
    else:
        period_days = 7
        total_periods = limit
    
    if not date_start:
        date_start = date_end - timedelta(days=period_days * total_periods)
    
    # Get data for each period
    history = []
    current_end = date_end
    
    for _ in range(total_periods):
        current_start = current_end - timedelta(days=period_days)
        
        # Get metrics for this period
        metrics = get_driver_efficiency_metrics(driver_id, current_start, current_end)
        earnings = get_driver_earnings_breakdown(driver_id, 'daily', current_start, current_end)
        
        total_earnings = sum(item['total_earnings'] for item in earnings)
        
        history.append({
            'period_start': current_start.isoformat(),
            'period_end': current_end.isoformat(),
            'deliveries': metrics['completed_deliveries'],
            'earnings': round(total_earnings, 2),
            'avg_delivery_time': metrics['avg_delivery_time_minutes'],
            'on_time_rate': metrics['on_time_delivery_rate'],
            'acceptance_rate': metrics['acceptance_rate'],
            'avg_rating': metrics['avg_rating'],
        })
        
        current_end = current_start
    
    # Reverse to chronological order
    history.reverse()
    
    # Cache for 30 minutes
    cache.set(cache_key, history, 1800)
    
    return history
