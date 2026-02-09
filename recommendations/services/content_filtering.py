"""
Content Filtering Service

This module provides content-based filtering for recommendations:
1. Trending items based on recent orders
2. Personalized recommendations based on user order history
"""

from datetime import timedelta
from django.db.models import Q, Count, Sum, Avg, F, Max
from django.utils import timezone
from decimal import Decimal

from restaurant.models import Restaurant, MenuItem
from order.models import Order, OrderItem
from review.models import Review
from authUser.models import User
from hungryBird.utils import calculate_distance
from recommendations.utils import (
    normalize_score,
    calculate_recency_weight,
    combine_weighted_scores,
)
from . import recommendation_engine


def calculate_item_popularity_score(menu_item_id, days=30):
    """
    Calculate comprehensive popularity score for a menu item.
    
    Combines order frequency, average rating, and recency into a single score.
    Weights: 50% frequency, 30% rating, 20% recency.
    
    Args:
        menu_item_id (int): Menu item primary key
        days (int): Number of days to look back for recency (default 30)
    
    Returns:
        float: Popularity score in range 0-100, or None if item doesn't exist
    
    Example:
        >>> score = calculate_item_popularity_score(menu_item_id=5, days=30)
        >>> score
        78.5
    """
    try:
        menu_item = MenuItem.objects.get(id=menu_item_id)
    except MenuItem.DoesNotExist:
        return None
    
    # Calculate time range
    date_threshold = timezone.now() - timedelta(days=days)
    
    # Count orders within time range
    order_count = OrderItem.objects.filter(
        menu_item_id=menu_item_id,
        order__status=5,  # Completed orders only
        order__is_active=True,
        order__created_at__gte=date_threshold
    ).count()
    
    # Get average rating
    avg_rating = Review.objects.filter(
        menu_item_id=menu_item_id,
        is_active=True
    ).aggregate(
        avg_rating=Avg('rating')
    )['avg_rating'] or 0.0
    
    # Get latest order date
    latest_order = OrderItem.objects.filter(
        menu_item_id=menu_item_id,
        order__status=5,
        order__is_active=True
    ).aggregate(
        latest_date=Max('order__created_at')
    )['latest_date']
    
    if latest_order is None:
        return 0.0
    
    # Get max order count for normalization
    max_orders = OrderItem.objects.filter(
        order__status=5,
        order__is_active=True,
        order__created_at__gte=date_threshold
    ).values('menu_item_id').annotate(
        count=Count('id')
    ).aggregate(max_count=Max('count'))['max_count'] or 1
    
    # Normalize scores
    frequency_score = normalize_score(order_count, 0, max_orders)
    rating_score = normalize_score(float(avg_rating), 0, 5.0)
    recency_score = calculate_recency_weight(latest_order.date(), max_days=days)
    
    # Combine scores
    popularity_score = combine_weighted_scores(
        frequency_score,
        rating_score,
        recency_score
    )
    
    return popularity_score


def get_trending_items_nearby(
    lat,
    lon,
    radius_km=10.0,
    days=30,
    limit=10,
    min_orders=5
):
    """
    Get trending menu items within a location radius based on recent orders.
    
    Returns items ordered frequently in the last N days from restaurants within
    the specified radius. Items must have at least min_orders orders to be
    considered trending.
    
    Args:
        lat (float): User's latitude
        lon (float): User's longitude
        radius_km (float): Search radius in kilometers (default 10.0)
        days (int): Number of days to look back (default 30)
        limit (int): Maximum number of results (default 10)
        min_orders (int): Minimum order count to be trending (default 5)
    
    Returns:
        list: List of dicts with keys:
            - id: MenuItem ID
            - name: Item name
            - price: Item price (decimal)
            - category: Item category
            - restaurant_id: Associated restaurant ID
            - restaurant_name: Associated restaurant name
            - times_ordered: Number of times ordered
            - average_rating: Average rating from reviews
            - image: Item image URL
            - distance_km: Distance from user
            - trending_score: Popularity score 0-100
    
    Example:
        >>> items = get_trending_items_nearby(
        ...     lat=40.7128,
        ...     lon=-74.0060,
        ...     days=30,
        ...     limit=10
        ... )
        >>> len(items)
        7
    """
    # Get restaurants within radius
    all_restaurants = Restaurant.objects.filter(
        is_active=True
    ).select_related('owner')
    
    restaurant_ids = []
    restaurant_map = {}  # Map ID to restaurant object
    
    for restaurant in all_restaurants:
        distance = calculate_distance(
            float(lat),
            float(lon),
            float(restaurant.latitude),
            float(restaurant.longitude)
        )
        if distance <= radius_km:
            restaurant_ids.append(restaurant.id)
            restaurant_map[restaurant.id] = (restaurant, distance)
    
    if not restaurant_ids:
        return []
    
    # Get time threshold
    date_threshold = timezone.now() - timedelta(days=days)
    
    # Get menu items from nearby restaurants with order counts
    queryset = MenuItem.objects.filter(
        restaurant_id__in=restaurant_ids,
        is_active=True
    ).select_related('restaurant').annotate(
        times_ordered=Count(
            'orderitem',
            filter=Q(
                orderitem__order__status=5,
                orderitem__order__is_active=True,
                orderitem__order__created_at__gte=date_threshold
            )
        ),
        avg_rating=Avg(
            'reviews__rating',
            filter=Q(reviews__is_active=True)
        ),
        latest_order_date=Max(
            'orderitem__order__created_at',
            filter=Q(
                orderitem__order__status=5,
                orderitem__order__is_active=True
            )
        )
    ).filter(
        times_ordered__gte=min_orders
    )
    
    # Build results with popularity scores
    results = []
    
    for item in queryset:
        # Calculate popularity score
        trending_score = calculate_item_popularity_score(item.id, days=days) or 0.0
        
        restaurant, distance = restaurant_map[item.restaurant_id]
        
        result = {
            'id': item.id,
            'name': item.name,
            'price': float(item.price),
            'category': item.category,
            'restaurant_id': item.restaurant_id,
            'restaurant_name': restaurant.name,
            'times_ordered': item.times_ordered,
            'average_rating': float(item.avg_rating) if item.avg_rating else None,
            'image': item.image.url if item.image else None,
            'distance_km': round(distance, 2),
            'trending_score': trending_score,
        }
        
        results.append(result)
    
    # Sort by trending score (highest first)
    results.sort(key=lambda x: -x['trending_score'])
    
    return results[:limit]


def get_personalized_recommendations(
    user_id,
    lat,
    lon,
    radius_km=10.0,
    limit=10,
    preferred_ratio=0.7,
    discovery_ratio=0.3
):
    """
    Get personalized recommendations based on user's order history.
    
    Analyzes the user's past orders to identify preferred categories and
    restaurants, then recommends items from those preferences (70%) and
    introduces new items from other categories (30%) for discovery.
    
    If the result doesn't reach the requested limit, falls back to
    trending nearby items to ensure user always gets recommendations.
    
    Args:
        user_id (int): Customer user ID
        lat (float): User's latitude
        lon (float): User's longitude
        radius_km (float): Search radius in kilometers (default 10.0)
        limit (int): Requested number of recommendations (default 10)
        preferred_ratio (float): Ratio of preferred category items (default 0.7)
        discovery_ratio (float): Ratio of discovery items (default 0.3)
    
    Returns:
        list: List of dicts with keys:
            - id: MenuItem ID
            - name: Item name
            - price: Item price
            - category: Item category
            - restaurant_id: Associated restaurant ID
            - restaurant_name: Associated restaurant name
            - average_rating: Average rating
            - image: Item image URL
            - distance_km: Distance from user
            - recommendation_reason: String explaining recommendation
    
    Example:
        >>> items = get_personalized_recommendations(
        ...     user_id=1,
        ...     lat=40.7128,
        ...     lon=-74.0060,
        ...     limit=10
        ... )
        >>> len(items)
        10
        >>> items[0]['recommendation_reason']
        'Based on your preferences'
    """
    try:
        user = User.objects.get(id=user_id, role=1)  # Customer only
    except User.DoesNotExist:
        return []
    
    # Get user's order history
    user_orders = Order.objects.filter(
        customer_id=user_id,
        status=5,
        is_active=True
    ).select_related('restaurant').prefetch_related('items')
    
    if not user_orders.exists():
        # User has no order history - use trending nearby as fallback
        return get_trending_items_nearby(lat, lon, radius_km, limit=limit)
    
    # Extract category preferences from order history
    category_counts = OrderItem.objects.filter(
        order__customer_id=user_id,
        order__status=5,
        order__is_active=True
    ).values('menu_item__category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    preferred_categories = [item['menu_item__category'] for item in category_counts[:3]]
    
    # Get nearby restaurants
    all_restaurants = Restaurant.objects.filter(
        is_active=True
    ).select_related('owner')
    
    restaurant_ids = []
    restaurant_map = {}
    
    for restaurant in all_restaurants:
        distance = calculate_distance(
            float(lat),
            float(lon),
            float(restaurant.latitude),
            float(restaurant.longitude)
        )
        if distance <= radius_km:
            restaurant_ids.append(restaurant.id)
            restaurant_map[restaurant.id] = (restaurant, distance)
    
    if not restaurant_ids:
        return []
    
    # Get items user has already ordered
    ordered_item_ids = OrderItem.objects.filter(
        order__customer_id=user_id
    ).values_list('menu_item_id', flat=True)
    
    # Calculate split limits
    preferred_limit = int(limit * preferred_ratio)
    discovery_limit = int(limit * discovery_ratio)
    
    results = []
    
    # 1. Preferred category items (70%)
    if preferred_categories:
        preferred_items = MenuItem.objects.filter(
            restaurant_id__in=restaurant_ids,
            category__in=preferred_categories,
            is_active=True
        ).exclude(
            id__in=ordered_item_ids
        ).select_related('restaurant').annotate(
            avg_rating=Avg(
                'reviews__rating',
                filter=Q(reviews__is_active=True)
            )
        ).order_by('-avg_rating')[:preferred_limit]
        
        for item in preferred_items:
            restaurant, distance = restaurant_map[item.restaurant_id]
            
            results.append({
                'id': item.id,
                'name': item.name,
                'price': float(item.price),
                'category': item.category,
                'restaurant_id': item.restaurant_id,
                'restaurant_name': restaurant.name,
                'average_rating': float(item.avg_rating) if item.avg_rating else None,
                'image': item.image.url if item.image else None,
                'distance_km': round(distance, 2),
                'recommendation_reason': 'Based on your preferences',
            })
    
    # 2. Discovery items from other categories (30%)
    if len(results) < limit:
        other_categories = [
            cat[0] for cat in MenuItem.CATEGORY_CHOICES
            if cat[0] not in preferred_categories
        ]
        
        discovery_items = MenuItem.objects.filter(
            restaurant_id__in=restaurant_ids,
            category__in=other_categories,
            is_active=True,
            reviews__rating__gte=4.0  # Only highly rated items
        ).exclude(
            id__in=ordered_item_ids
        ).select_related('restaurant').annotate(
            avg_rating=Avg(
                'reviews__rating',
                filter=Q(reviews__is_active=True)
            )
        ).filter(
            avg_rating__gte=4.0
        ).order_by('-avg_rating').distinct()[:discovery_limit]
        
        for item in discovery_items:
            if item.id not in [r['id'] for r in results]:  # Avoid duplicates
                restaurant, distance = restaurant_map[item.restaurant_id]
                
                results.append({
                    'id': item.id,
                    'name': item.name,
                    'price': float(item.price),
                    'category': item.category,
                    'restaurant_id': item.restaurant_id,
                    'restaurant_name': restaurant.name,
                    'average_rating': float(item.avg_rating) if item.avg_rating else None,
                    'image': item.image.url if item.image else None,
                    'distance_km': round(distance, 2),
                    'recommendation_reason': 'Highly rated in your area',
                })
    
    # 3. Fallback: If still not enough results, use trending nearby
    if len(results) < limit:
        trending = get_trending_items_nearby(lat, lon, radius_km, limit=limit * 2)
        
        for item in trending:
            if item['id'] not in [r['id'] for r in results]:
                results.append({
                    'id': item['id'],
                    'name': item['name'],
                    'price': item['price'],
                    'category': item['category'],
                    'restaurant_id': item['restaurant_id'],
                    'restaurant_name': item['restaurant_name'],
                    'average_rating': item['average_rating'],
                    'image': item['image'],
                    'distance_km': item['distance_km'],
                    'recommendation_reason': 'Popular in your area',
                })
                
                if len(results) >= limit:
                    break
    
    return results[:limit]
