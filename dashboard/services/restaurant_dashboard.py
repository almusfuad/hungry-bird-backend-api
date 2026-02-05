from django.db.models import Count, Sum, Avg, Q, F, Case, When, DecimalField, Max
from django.db.models.functions import TruncDate, TruncMonth
from order.models import Order
from payment.models import Payment
from restaurant.models import MenuItem
from authUser.models import User
from datetime import datetime, timedelta


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
