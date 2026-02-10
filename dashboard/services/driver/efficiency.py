"""Driver efficiency metrics.

Acceptance rate, delivery speed, distance efficiency, and reliability scores.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from django.core.cache import cache

from order.models import Order
from hungryBird.utils import calculate_distance


def get_driver_efficiency_metrics(
    driver_id: int,
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get comprehensive driver efficiency metrics.
    
    Args:
        driver_id: Driver user ID.
        date_start: Start date for filtering (inclusive).
        date_end: End date for filtering (inclusive).
        
    Returns:
        Dictionary containing efficiency metrics including acceptance rate,
        delivery speed, distance efficiency, and reliability scores.
    """
    cache_key = f"driver_efficiency_{driver_id}_{date_start}_{date_end}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # All orders assigned to driver
    all_orders = Order.objects.filter(driver_id=driver_id, is_active=True)
    
    if date_start:
        all_orders = all_orders.filter(created_at__gte=date_start)
    if date_end:
        all_orders = all_orders.filter(created_at__lte=date_end)
    
    total_assigned = all_orders.count()
    
    # Completed deliveries
    completed_orders = all_orders.filter(status__in=[5, 7]).prefetch_related('statustransitions')
    completed_count = completed_orders.count()
    
    # Cancelled or rejected orders
    cancelled_count = all_orders.filter(status=6).count()
    
    # Calculate acceptance rate
    acceptance_rate = round((completed_count / total_assigned * 100), 2) if total_assigned > 0 else 0
    
    # Delivery time and distance metrics
    delivery_times = []
    distances = []
    speeds = []  # km per hour
    
    for order in completed_orders:
        pickup = order.statustransitions.filter(to_status=4).first()
        delivered = order.statustransitions.filter(to_status=5).first()
        
        if pickup and delivered:
            # Delivery time in minutes
            time_minutes = (delivered.transitioned_at - pickup.transitioned_at).total_seconds() / 60
            delivery_times.append(time_minutes)
            
            # Distance calculation
            if pickup.driver_location_lat and pickup.driver_location_lon:
                distance = calculate_distance(
                    pickup.driver_location_lat,
                    pickup.driver_location_lon,
                    order.delivery_latitude,
                    order.delivery_longitude
                )
                distances.append(distance)
                
                # Speed calculation (km/h)
                if time_minutes > 0:
                    speed = (distance / time_minutes) * 60
                    speeds.append(speed)
    
    # Calculate averages and efficiency scores
    avg_delivery_time = round(sum(delivery_times) / len(delivery_times), 2) if delivery_times else 0
    avg_distance = round(sum(distances) / len(distances), 2) if distances else 0
    avg_speed = round(sum(speeds) / len(speeds), 2) if speeds else 0
    
    # Distance per hour worked (approximation)
    total_distance = sum(distances)
    total_time_hours = sum(delivery_times) / 60 if delivery_times else 0
    distance_per_hour = round(total_distance / total_time_hours, 2) if total_time_hours > 0 else 0
    
    # Deliveries per hour
    deliveries_per_hour = round(len(delivery_times) / total_time_hours, 2) if total_time_hours > 0 else 0
    
    # Calculate on-time delivery rate (assuming 30 min standard)
    on_time_count = sum(1 for t in delivery_times if t <= 30)
    on_time_rate = round((on_time_count / len(delivery_times) * 100), 2) if delivery_times else 0
    
    # Note: Driver rating would come from Order reviews where driver is involved
    # For now, set to 0 as there's no separate DriverReview model
    avg_rating = 0.0
    
    metrics = {
        'total_assigned_orders': total_assigned,
        'completed_deliveries': completed_count,
        'cancelled_orders': cancelled_count,
        'acceptance_rate': acceptance_rate,
        'avg_delivery_time_minutes': avg_delivery_time,
        'avg_distance_km': avg_distance,
        'avg_speed_kmh': avg_speed,
        'distance_per_hour': distance_per_hour,
        'deliveries_per_hour': deliveries_per_hour,
        'on_time_delivery_rate': on_time_rate,
        'avg_rating': avg_rating,
        'total_distance_km': round(total_distance, 2),
        'total_time_hours': round(total_time_hours, 2),
    }
    
    # Cache for 30 minutes
    cache.set(cache_key, metrics, 1800)
    
    return metrics
