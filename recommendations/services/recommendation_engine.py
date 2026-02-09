"""
Recommendation Engine Service

This module provides core recommendation logic for:
1. Nearby restaurants based on user location
2. Popular items by category and location
"""

from django.db.models import Q, Count, Avg
from restaurant.models import Restaurant, MenuItem
from order.models import Order, OrderItem
from hungryBird.utils import calculate_distance


def get_nearby_restaurants(
    lat,
    lon,
    radius_km=10.0,
    category=None,
    min_rating=None,
    limit=10
):
    """
    Get restaurants near a given location using Haversine distance calculation.
    
    Filters active restaurants within the specified radius, optionally by category
    and minimum rating. Results are sorted by distance (nearest first) then by
    popularity (order count).
    
    Args:
        lat (float): User's latitude
        lon (float): User's longitude
        radius_km (float): Search radius in kilometers (default 10.0)
        category (str): Optional category filter from MenuItem.CATEGORY_CHOICES
        min_rating (float): Optional minimum average rating filter (1.0-5.0)
        limit (int): Maximum number of results (default 10)
    
    Returns:
        list: List of dicts with keys:
            - id: Restaurant ID
            - name: Restaurant name
            - address: Restaurant address
            - latitude: Restaurant latitude
            - longitude: Restaurant longitude
            - distance_km: Distance from user in kilometers
            - order_count: Number of completed orders
            - average_rating: Average rating from reviews (decimal)
            - image: Restaurant image URL (nullable)
    
    Example:
        >>> restaurants = get_nearby_restaurants(
        ...     lat=40.7128,
        ...     lon=-74.0060,
        ...     radius_km=5.0,
        ...     min_rating=4.0,
        ...     limit=10
        ... )
        >>> len(restaurants)
        5
        >>> restaurants[0]['distance_km']
        2.35
    """
    # Base queryset: active restaurants with relationships
    queryset = Restaurant.objects.filter(
        is_active=True
    ).select_related(
        'owner'
    ).prefetch_related(
        'menu_items',
        'drivers'
    )
    
    # Annotate with order count (completed orders only)
    queryset = queryset.annotate(
        order_count=Count(
            'orders',
            filter=Q(orders__status=5, orders__is_active=True)
        )
    )
    
    # Collect results with distance calculation
    restaurants_with_distance = []
    
    for restaurant in queryset:
        # Calculate distance using Haversine formula
        distance = calculate_distance(
            float(lat),
            float(lon),
            float(restaurant.latitude),
            float(restaurant.longitude)
        )
        
        # Filter by radius
        if distance > radius_km:
            continue
        
        # Filter by minimum rating if specified
        if min_rating is not None:
            avg_rating = restaurant.get_average_rating()
            if avg_rating is None or float(avg_rating) < float(min_rating):
                continue
        
        # Check if restaurant is available (if field exists)
        if hasattr(restaurant, 'is_available') and not restaurant.is_available:
            continue
        
        # Build result dict
        result = {
            'id': restaurant.id,
            'name': restaurant.name,
            'address': restaurant.address,
            'latitude': float(restaurant.latitude),
            'longitude': float(restaurant.longitude),
            'distance_km': round(distance, 2),
            'order_count': restaurant.order_count,
            'average_rating': float(restaurant.get_average_rating()) if restaurant.get_average_rating() else None,
            'image': restaurant.image.url if restaurant.image else None,
        }
        
        restaurants_with_distance.append(result)
    
    # Sort by distance (nearest first), then by order count (most popular)
    restaurants_with_distance.sort(
        key=lambda x: (x['distance_km'], -x['order_count'])
    )
    
    return restaurants_with_distance[:limit]


def get_popular_items_by_category(
    category,
    lat=None,
    lon=None,
    radius_km=10.0,
    limit=10,
    min_orders=5
):
    """
    Get popular menu items by category, optionally filtered by location.
    
    Returns items that have been ordered at least min_orders times, sorted by
    order frequency. If location is provided, filters to restaurants within
    the specified radius.
    
    Args:
        category (str): MenuItem category (from MenuItem.CATEGORY_CHOICES)
        lat (float): Optional user latitude for location filtering
        lon (float): Optional user longitude for location filtering
        radius_km (float): Search radius if lat/lon provided (default 10.0)
        limit (int): Maximum number of results (default 10)
        min_orders (int): Minimum number of orders to be considered popular (default 5)
    
    Returns:
        list: List of dicts with keys:
            - id: MenuItem ID
            - name: Item name
            - price: Item price (decimal)
            - category: Item category
            - restaurant_id: Associated restaurant ID
            - restaurant_name: Associated restaurant name
            - times_ordered: Number of times ordered
            - average_rating: Average rating from reviews (decimal)
            - image: Item image URL (nullable)
            - distance_km: Distance from user (if location filtering used)
    
    Example:
        >>> items = get_popular_items_by_category(
        ...     category='MAIN',
        ...     lat=40.7128,
        ...     lon=-74.0060,
        ...     limit=10
        ... )
        >>> len(items)
        8
        >>> items[0]['times_ordered']
        25
    """
    # Validate category exists in choices
    valid_categories = dict(MenuItem.CATEGORY_CHOICES)
    if category not in valid_categories:
        return []
    
    # Determine restaurants to query from
    if lat is not None and lon is not None:
        # Filter by location radius
        all_restaurants = Restaurant.objects.filter(
            is_active=True
        ).select_related('owner').prefetch_related('menu_items')
        
        restaurant_ids = []
        for restaurant in all_restaurants:
            distance = calculate_distance(
                float(lat),
                float(lon),
                float(restaurant.latitude),
                float(restaurant.longitude)
            )
            if distance <= radius_km:
                restaurant_ids.append(restaurant.id)
        
        if not restaurant_ids:
            return []
        
        queryset = MenuItem.objects.filter(
            restaurant_id__in=restaurant_ids,
            category=category,
            is_active=True
        )
    else:
        # No location filtering
        queryset = MenuItem.objects.filter(
            category=category,
            is_active=True,
            restaurant__is_active=True
        )
    
    # Annotate with order count and rating
    queryset = queryset.select_related('restaurant').annotate(
        times_ordered=Count(
            'orderitem',
            filter=Q(orderitem__order__status=5, orderitem__order__is_active=True)
        ),
        avg_rating=Avg(
            'reviews__rating',
            filter=Q(reviews__is_active=True)
        )
    )
    
    # Filter by minimum order count
    queryset = queryset.filter(times_ordered__gte=min_orders)
    
    # Order by times_ordered descending
    queryset = queryset.order_by('-times_ordered')[:limit]
    
    # Build result list
    results = []
    for item in queryset:
        result = {
            'id': item.id,
            'name': item.name,
            'price': float(item.price),
            'category': item.category,
            'restaurant_id': item.restaurant_id,
            'restaurant_name': item.restaurant.name,
            'times_ordered': item.times_ordered,
            'average_rating': float(item.avg_rating) if item.avg_rating else None,
            'image': item.image.url if item.image else None,
        }
        
        # Add distance if location filtering was used
        if lat is not None and lon is not None:
            distance = calculate_distance(
                float(lat),
                float(lon),
                float(item.restaurant.latitude),
                float(item.restaurant.longitude)
            )
            result['distance_km'] = round(distance, 2)
        
        results.append(result)
    
    return results
