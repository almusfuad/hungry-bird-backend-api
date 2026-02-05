from django.db.models import Count, Sum, Avg, Max, Min
from django.db.models.functions import TruncMonth
from order.models import Order
from restaurant.models import Restaurant


def get_customer_overview(customer_id, date_start=None, date_end=None):
    """Get customer's order history and statistics."""
    queryset = Order.objects.filter(customer_id=customer_id)
    
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    
    # Monthly spending
    monthly_stats = queryset.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        orders=Count('id'),
        spent=Sum('total_price')
    ).order_by('-month')
    
    # Favorite restaurants
    favorite_restaurants = Restaurant.objects.filter(
        orders__customer_id=customer_id
    ).annotate(
        order_count=Count('orders')
    ).order_by('-order_count')[:3].values('id', 'name', 'order_count')
    
    # Recent orders
    recent_orders = queryset.select_related('restaurant').order_by('-created_at')[:10].values(
        'id', 'restaurant__name', 'total_price', 'status', 'created_at'
    )
    
    # Overall stats
    overall = queryset.aggregate(
        total_orders=Count('id'),
        total_spent=Sum('total_price'),
        avg_order_value=Avg('total_price')
    )
    
    return {
        'overall': overall,
        'monthly_stats': list(monthly_stats),
        'favorite_restaurants': list(favorite_restaurants),
        'recent_orders': list(recent_orders)
    }
