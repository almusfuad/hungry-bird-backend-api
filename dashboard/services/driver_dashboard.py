from django.db.models import Count, Sum, Avg, Q
from order.models import Order
from dashboard.models import OrderStatusTransition
from hungryBird.utils import calculate_distance


def get_driver_overview(driver_id, date_start=None, date_end=None):
    """Get driver's delivery statistics and earnings."""
    queryset = Order.objects.filter(driver_id=driver_id, status=5)
    
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    
    orders = queryset.prefetch_related('statustransitions')
    
    total_deliveries = 0
    total_distance = 0
    total_time = 0
    total_earnings = 0
    
    for order in orders:
        pickup = order.statustransitions.filter(to_status=4).first()
        delivered = order.statustransitions.filter(to_status=5).first()
        
        if pickup and delivered:
            # Delivery time
            time_minutes = (delivered.transitioned_at - pickup.transitioned_at).total_seconds() / 60
            total_time += time_minutes
            
            # Distance
            if pickup.driver_location_lat and pickup.driver_location_lon:
                distance = calculate_distance(
                    pickup.driver_location_lat,
                    pickup.driver_location_lon,
                    order.delivery_latitude,
                    order.delivery_longitude
                )
                total_distance += distance
            
            total_deliveries += 1
            total_earnings += float(order.total_price)
    
    return {
        'total_deliveries': total_deliveries,
        'total_distance_km': round(total_distance, 2),
        'avg_distance_km': round(total_distance / total_deliveries, 2) if total_deliveries > 0 else 0,
        'avg_delivery_minutes': round(total_time / total_deliveries, 2) if total_deliveries > 0 else 0,
        'total_earnings': round(total_earnings, 2)
    }
