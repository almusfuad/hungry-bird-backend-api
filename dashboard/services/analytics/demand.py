"""Demand pattern analytics.

Analysis and prediction of demand patterns by time and day.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from django.core.cache import cache
from django.db.models import Count, Sum, Avg
from django.utils import timezone

from order.models import Order
from dashboard.models import OrderStatusTransition


def predict_demand_patterns(
    restaurant_id: Optional[int] = None,
    analysis_days: int = 30
) -> Dict[str, Any]:
    """Analyze and predict demand patterns by day of week and hour.
    
    Args:
        restaurant_id: Restaurant ID for restaurant-specific analysis.
                      If None, analyzes platform-wide patterns.
        analysis_days: Number of days of historical data to analyze.
        
    Returns:
        Dictionary containing demand patterns by day of week,
        peak hours, and demand predictions.
    """
    cache_key = f"demand_patterns_{restaurant_id}_{analysis_days}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=analysis_days)
    
    queryset = Order.objects.filter(
        is_active=True,
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    if restaurant_id:
        queryset = queryset.filter(restaurant_id=restaurant_id)
    
    # Analyze by day of week
    day_of_week_data = []
    for day in range(7):  # 0=Monday, 6=Sunday
        day_orders = queryset.filter(created_at__week_day=(day + 2) % 7 + 1)
        day_metrics = day_orders.aggregate(
            order_count=Count('id'),
            revenue=Sum('total_price'),
            avg_order_value=Avg('total_price')
        )
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_of_week_data.append({
            'day': day_names[day],
            'day_number': day,
            'order_count': day_metrics['order_count'] or 0,
            'revenue': float(day_metrics['revenue'] or 0),
            'avg_order_value': float(day_metrics['avg_order_value'] or 0),
        })
    
    # Analyze by hour of day
    hourly_data = []
    for hour in range(24):
        hour_orders = queryset.filter(created_at__hour=hour)
        hour_metrics = hour_orders.aggregate(
            order_count=Count('id'),
            revenue=Sum('total_price')
        )
        
        hourly_data.append({
            'hour': hour,
            'order_count': hour_metrics['order_count'] or 0,
            'revenue': float(hour_metrics['revenue'] or 0),
        })
    
    # Identify peak hours (top 3)
    sorted_hours = sorted(hourly_data, key=lambda x: x['order_count'], reverse=True)
    peak_hours = sorted_hours[:3]
    
    # Identify busiest days
    sorted_days = sorted(day_of_week_data, key=lambda x: x['order_count'], reverse=True)
    busiest_days = sorted_days[:3]
    
    # Calculate average delivery time patterns using OrderStatusTransition
    delivery_times = []
    transitions = OrderStatusTransition.objects.filter(
        order__in=queryset,
        to_status=5  # Delivered status
    ).select_related('order')
    
    for transition in transitions:
        pickup_transition = OrderStatusTransition.objects.filter(
            order=transition.order,
            to_status=4  # Out for delivery
        ).first()
        
        if pickup_transition:
            delivery_time = (transition.transitioned_at - pickup_transition.transitioned_at).total_seconds() / 60
            delivery_times.append(delivery_time)
    
    avg_delivery_time = round(sum(delivery_times) / len(delivery_times), 2) if delivery_times else 0
    
    result = {
        'analysis_period_days': analysis_days,
        'day_of_week_patterns': day_of_week_data,
        'hourly_patterns': hourly_data,
        'peak_hours': peak_hours,
        'busiest_days': busiest_days,
        'avg_delivery_time_minutes': avg_delivery_time,
        'total_orders_analyzed': queryset.count(),
    }
    
    # Cache for 30 minutes
    cache.set(cache_key, result, 1800)
    
    return result
