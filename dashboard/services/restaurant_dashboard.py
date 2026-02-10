"""Restaurant dashboard analytics service.

This module provides performance metrics and analytics for restaurant owners.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from django.db.models import Count, Sum, Avg, Q, F, Case, When, DecimalField, Max
from django.db.models.functions import TruncDate, TruncMonth, TruncHour
from django.core.cache import cache
from django.utils import timezone

from order.models import Order
from payment.models import Payment
from restaurant.models import MenuItem
from authUser.models import User


def get_daily_orders(restaurant_id, date_start=None, date_end=None, order_source=None):
    """Get daily order statistics for a restaurant."""
    queryset = Order.objects.filter(restaurant_id=restaurant_id)
    
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    if order_source:
        queryset = queryset.filter(order_source=order_source)
    
    results = queryset.annotate(
        date=TruncDate('created_at')
    ).values('date', 'order_source').annotate(
        total_orders=Count('id'),
        revenue=Sum('total_price'),
        avg_order_value=Avg('total_price'),
        completed=Count(Case(When(Q(status=5) | Q(status=7), then=1))),
        cancelled=Count(Case(When(status=6, then=1))),
        pending=Count(Case(When(status=1, then=1)))
    ).order_by('-date')
    
    return list(results)


def get_order_source_comparison(restaurant_id, date_start=None, date_end=None):
    """Compare POS vs Online orders with payment breakdown."""
    queryset = Order.objects.filter(restaurant_id=restaurant_id)
    
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    
    results = queryset.values('order_source').annotate(
        total_orders=Count('id'),
        total_revenue=Sum('total_price'),
        avg_order_value=Avg('total_price'),
        completed=Count(Case(When(Q(status=5) | Q(status=7), then=1))),
        cancelled=Count(Case(When(status=6, then=1))),
        # Payment method breakdown
        cod_payments=Count(Case(When(payment__payment_method=1, then=1))),
        stripe_payments=Count(Case(When(payment__payment_method=2, then=1))),
        cash_payments=Count(Case(When(payment__payment_method=3, then=1))),
        mfs_payments=Count(Case(When(payment__payment_method=4, then=1))),
        card_payments=Count(Case(When(payment__payment_method=5, then=1)))
    ).order_by('order_source')
    
    return list(results)


def get_top_customers(restaurant_id, date_start=None, date_end=None, limit=50):
    """Get top customers by total spent."""
    queryset = Order.objects.filter(restaurant_id=restaurant_id)
    
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    
    results = User.objects.filter(
        role=1,
        id__in=queryset.values_list('customer_id', flat=True)
    ).annotate(
        order_count=Count('orders', filter=Q(orders__restaurant_id=restaurant_id)),
        total_spent=Sum('orders__total_price', filter=Q(orders__restaurant_id=restaurant_id)),
        avg_order_value=Avg('orders__total_price', filter=Q(orders__restaurant_id=restaurant_id)),
        last_order_date=Max('orders__created_at', filter=Q(orders__restaurant_id=restaurant_id))
    ).order_by('-total_spent')[:limit]
    
    return list(results.values(
        'id', 'username', 'first_name', 'last_name', 'email',
        'order_count', 'total_spent', 'avg_order_value', 'last_order_date'
    ))


def get_popular_items(restaurant_id, date_start=None, date_end=None, limit=20):
    """Get most popular menu items by order frequency."""
    order_filter = Q(orderitem__order__restaurant_id=restaurant_id)
    
    if date_start:
        order_filter &= Q(orderitem__order__created_at__gte=date_start)
    if date_end:
        order_filter &= Q(orderitem__order__created_at__lte=date_end)
    
    results = MenuItem.objects.filter(restaurant_id=restaurant_id).annotate(
        times_ordered=Count('orderitem__order', distinct=True, filter=order_filter),
        total_quantity=Sum('orderitem__quantity', filter=order_filter),
        total_revenue=Sum(F('orderitem__quantity') * F('price'), filter=order_filter),
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_active=True))
    ).filter(times_ordered__gt=0).order_by('-times_ordered')[:limit]
    
    return list(results.values(
        'id', 'name', 'category', 'price',
        'times_ordered', 'total_quantity', 'total_revenue', 'avg_rating'
    ))


def get_driver_performance(restaurant_id, driver_id=None, date_start=None, date_end=None):
    """Get driver delivery performance with time and distance tracking."""
    from dashboard.models import OrderStatusTransition
    from hungryBird.utils import calculate_distance
    
    queryset = Order.objects.filter(
        restaurant_id=restaurant_id,
        driver_id__isnull=False,
        status=5
    )
    
    if driver_id:
        queryset = queryset.filter(driver_id=driver_id)
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    
    orders = queryset.select_related('restaurant', 'driver').prefetch_related('statustransitions')
    
    driver_stats = {}
    
    for order in orders:
        # Get status transitions
        pickup = order.statustransitions.filter(to_status=4).first()
        delivered = order.statustransitions.filter(to_status=5).first()
        
        if not pickup or not delivered:
            continue
        
        # Calculate delivery time
        delivery_time = (delivered.transitioned_at - pickup.transitioned_at).total_seconds() / 60
        
        # Calculate distance using actual pickup location
        distance_km = 0
        if pickup.driver_location_lat and pickup.driver_location_lon:
            distance_km = calculate_distance(
                pickup.driver_location_lat,
                pickup.driver_location_lon,
                order.delivery_latitude,
                order.delivery_longitude
            )
        
        # Aggregate by driver
        driver_key = order.driver_id
        if driver_key not in driver_stats:
            driver_stats[driver_key] = {
                'driver_id': order.driver_id,
                'driver_name': order.driver.get_full_name() or order.driver.username,
                'deliveries': [],
                'total_earnings': 0
            }
        
        driver_stats[driver_key]['deliveries'].append({
            'time': delivery_time,
            'distance': distance_km
        })
        driver_stats[driver_key]['total_earnings'] += float(order.total_price)
    
    # Calculate averages
    results = []
    for driver_id, stats in driver_stats.items():
        deliveries = stats['deliveries']
        results.append({
            'driver_id': stats['driver_id'],
            'driver_name': stats['driver_name'],
            'total_deliveries': len(deliveries),
            'avg_delivery_minutes': sum(d['time'] for d in deliveries) / len(deliveries) if deliveries else 0,
            'total_distance_km': sum(d['distance'] for d in deliveries),
            'avg_distance_km': sum(d['distance'] for d in deliveries) / len(deliveries) if deliveries else 0,
            'total_earnings': stats['total_earnings']
        })
    
    return sorted(results, key=lambda x: x['total_deliveries'], reverse=True)


def get_period_comparison(
    restaurant_id: int,
    comparison_type: str = 'mom',
    current_period_start: Optional[datetime] = None,
    current_period_end: Optional[datetime] = None
) -> Dict[str, Any]:
    """Compare current period metrics with previous period.
    
    Args:
        restaurant_id: Restaurant ID.
        comparison_type: Type of comparison - 'mom' (month-over-month),
                        'wow' (week-over-week), or 'yoy' (year-over-year).
        current_period_start: Start of current period.
        current_period_end: End of current period.
        
    Returns:
        Dictionary containing current and previous period metrics
        with growth rate calculations.
    """
    cache_key = f"period_comparison_{restaurant_id}_{comparison_type}_{current_period_start}_{current_period_end}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # Determine time delta
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
    current_metrics = _get_restaurant_period_metrics(
        restaurant_id,
        current_period_start,
        current_period_end
    )
    
    # Get previous period metrics
    previous_metrics = _get_restaurant_period_metrics(
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


def _get_restaurant_period_metrics(
    restaurant_id: int,
    period_start: datetime,
    period_end: datetime
) -> Dict[str, Any]:
    """Get metrics for a restaurant in a specific time period.
    
    Args:
        restaurant_id: Restaurant ID.
        period_start: Start of period.
        period_end: End of period.
        
    Returns:
        Dictionary containing period metrics.
    """
    queryset = Order.objects.filter(
        restaurant_id=restaurant_id,
        is_active=True,
        created_at__gte=period_start,
        created_at__lte=period_end
    )
    
    metrics = queryset.aggregate(
        revenue=Sum('total_price'),
        order_count=Count('id'),
        avg_order_value=Avg('total_price'),
        unique_customers=Count('customer', distinct=True),
        completed=Count(Case(When(Q(status=5) | Q(status=7), then=1))),
        cancelled=Count(Case(When(status=6, then=1))),
        online_orders=Count(Case(When(order_source=1, then=1))),
        pos_orders=Count(Case(When(order_source=2, then=1))),
    )
    
    return {
        'revenue': float(metrics['revenue'] or 0),
        'order_count': metrics['order_count'] or 0,
        'avg_order_value': float(metrics['avg_order_value'] or 0),
        'unique_customers': metrics['unique_customers'] or 0,
        'completed_orders': metrics['completed'] or 0,
        'cancelled_orders': metrics['cancelled'] or 0,
        'online_orders': metrics['online_orders'] or 0,
        'pos_orders': metrics['pos_orders'] or 0,
    }


def get_peak_hours_analysis(
    restaurant_id: int,
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None
) -> Dict[str, Any]:
    """Analyze peak ordering hours and day-of-week patterns.
    
    Args:
        restaurant_id: Restaurant ID.
        date_start: Start date for analysis.
        date_end: End date for analysis.
        
    Returns:
        Dictionary containing peak hours, busiest days, and patterns.
    """
    cache_key = f"peak_hours_{restaurant_id}_{date_start}_{date_end}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    if not date_end:
        date_end = timezone.now()
    if not date_start:
        date_start = date_end - timedelta(days=30)
    
    queryset = Order.objects.filter(
        restaurant_id=restaurant_id,
        is_active=True,
        created_at__gte=date_start,
        created_at__lte=date_end
    )
    
    # Hourly analysis
    hourly_data = []
    for hour in range(24):
        hour_orders = queryset.filter(created_at__hour=hour)
        hour_metrics = hour_orders.aggregate(
            order_count=Count('id'),
            revenue=Sum('total_price'),
            avg_order_value=Avg('total_price')
        )
        
        hourly_data.append({
            'hour': hour,
            'order_count': hour_metrics['order_count'] or 0,
            'revenue': float(hour_metrics['revenue'] or 0),
            'avg_order_value': float(hour_metrics['avg_order_value'] or 0),
        })
    
    # Day of week analysis
    day_of_week_data = []
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day in range(7):
        # Django week_day: 1=Sunday, 2=Monday, ..., 7=Saturday
        day_orders = queryset.filter(created_at__week_day=(day + 2) % 7 + 1)
        day_metrics = day_orders.aggregate(
            order_count=Count('id'),
            revenue=Sum('total_price'),
            avg_order_value=Avg('total_price')
        )
        
        day_of_week_data.append({
            'day': day_names[day],
            'day_number': day,
            'order_count': day_metrics['order_count'] or 0,
            'revenue': float(day_metrics['revenue'] or 0),
            'avg_order_value': float(day_metrics['avg_order_value'] or 0),
        })
    
    # Identify peak hours (top 3 by order count)
    sorted_hours = sorted(hourly_data, key=lambda x: x['order_count'], reverse=True)
    peak_hours = sorted_hours[:3]
    
    # Identify busiest days
    sorted_days = sorted(day_of_week_data, key=lambda x: x['order_count'], reverse=True)
    busiest_days = sorted_days[:3]
    
    result = {
        'analysis_period': {
            'start': date_start.isoformat(),
            'end': date_end.isoformat(),
        },
        'hourly_patterns': hourly_data,
        'day_of_week_patterns': day_of_week_data,
        'peak_hours': peak_hours,
        'busiest_days': busiest_days,
        'total_orders': queryset.count(),
    }
    
    # Cache for 30 minutes
    cache.set(cache_key, result, 1800)
    
    return result


def get_customer_retention_metrics(
    restaurant_id: int,
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None
) -> Dict[str, Any]:
    """Calculate customer retention and repeat customer metrics.
    
    Args:
        restaurant_id: Restaurant ID.
        date_start: Start date for analysis.
        date_end: End date for analysis.
        
    Returns:
        Dictionary containing retention rate, repeat customer rate,
        and average days between orders.
    """
    cache_key = f"customer_retention_{restaurant_id}_{date_start}_{date_end}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    if not date_end:
        date_end = timezone.now()
    if not date_start:
        date_start = date_end - timedelta(days=30)
    
    # Get all customers who ordered in the period
    order_filter = Q(
        orders__restaurant_id=restaurant_id,
        orders__is_active=True,
        orders__created_at__gte=date_start,
        orders__created_at__lte=date_end
    )
    
    customers = User.objects.filter(
        role=1,
        is_active=True
    ).annotate(
        order_count=Count('orders', filter=order_filter),
        first_order=Min('orders__created_at', filter=order_filter),
        last_order=Max('orders__created_at', filter=order_filter),
        total_spent=Sum('orders__total_price', filter=order_filter),
    ).filter(order_count__gt=0)
    
    total_customers = customers.count()
    
    # Customer segmentation
    one_time_buyers = customers.filter(order_count=1).count()
    repeat_customers = customers.filter(order_count__gte=2).count()
    loyal_customers = customers.filter(order_count__gte=5).count()
    
    # Calculate average days between orders for repeat customers
    avg_days_between_orders = 0
    if repeat_customers > 0:
        days_between_list = []
        for customer in customers.filter(order_count__gte=2):
            if customer.first_order and customer.last_order:
                days = (customer.last_order - customer.first_order).days
                if customer.order_count > 1:
                    avg_days = days / (customer.order_count - 1)
                    days_between_list.append(avg_days)
        
        if days_between_list:
            avg_days_between_orders = round(sum(days_between_list) / len(days_between_list), 2)
    
    # Calculate retention rate
    retention_rate = round((repeat_customers / total_customers * 100), 2) if total_customers > 0 else 0
    
    # Calculate customer lifetime value
    avg_customer_lifetime_value = customers.aggregate(
        avg_ltv=Avg('total_spent')
    )['avg_ltv']
    
    result = {
        'analysis_period': {
            'start': date_start.isoformat(),
            'end': date_end.isoformat(),
        },
        'total_customers': total_customers,
        'one_time_buyers': one_time_buyers,
        'repeat_customers': repeat_customers,
        'loyal_customers': loyal_customers,
        'retention_rate': retention_rate,
        'repeat_customer_rate': round((repeat_customers / total_customers * 100), 2) if total_customers > 0 else 0,
        'avg_days_between_orders': avg_days_between_orders,
        'avg_customer_lifetime_value': float(avg_customer_lifetime_value or 0),
    }
    
    # Cache for 30 minutes
    cache.set(cache_key, result, 1800)
    
    return result

