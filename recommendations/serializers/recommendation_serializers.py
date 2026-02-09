"""
Serializers for Recommendation API

Handles validation and serialization of:
1. Location-based filter inputs
2. Recommended restaurant data
3. Recommended menu item data
"""

from decimal import Decimal
from rest_framework import serializers
from restaurant.models import MenuItem


class LocationFilterSerializer(serializers.Serializer):
    """
    Serializer for validating location-based query parameters.
    
    Used to validate and parse latitude, longitude, radius, and optional filters
    for recommendation endpoints.
    """
    
    lat = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=True,
        help_text='User latitude in decimal degrees'
    )
    lon = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=True,
        help_text='User longitude in decimal degrees'
    )
    radius = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=Decimal('10.0'),
        min_value=Decimal('0.1'),
        max_value=Decimal('50.0'),
        help_text='Search radius in kilometers (default: 10.0, max: 50.0)'
    )
    category = serializers.ChoiceField(
        choices=MenuItem.CATEGORY_CHOICES,
        required=False,
        allow_blank=True,
        help_text='Optional menu item category filter'
    )
    min_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        required=False,
        min_value=Decimal('1.0'),
        max_value=Decimal('5.0'),
        help_text='Minimum average rating filter (1.0-5.0)'
    )
    
    def validate_category(self, value):
        """Validate category is in valid choices if provided."""
        if not value:  # Allow empty string
            return None
        
        valid_categories = dict(MenuItem.CATEGORY_CHOICES)
        if value not in valid_categories:
            raise serializers.ValidationError(
                f'Invalid category. Must be one of: {", ".join(valid_categories.keys())}'
            )
        return value


class RecommendedRestaurantSerializer(serializers.Serializer):
    """
    Serializer for recommended restaurant data.
    
    Represents a restaurant recommendation with location, distance, and
    popularity metrics.
    """
    
    id = serializers.IntegerField(
        help_text='Restaurant ID'
    )
    name = serializers.CharField(
        max_length=255,
        help_text='Restaurant name'
    )
    address = serializers.CharField(
        help_text='Restaurant address'
    )
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text='Restaurant latitude'
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text='Restaurant longitude'
    )
    distance_km = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Distance from user in kilometers'
    )
    order_count = serializers.IntegerField(
        help_text='Number of completed orders'
    )
    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        allow_null=True,
        help_text='Average rating from reviews (1.0-5.0 scale)'
    )
    image = serializers.SerializerMethodField(
        help_text='Restaurant image URL'
    )
    
    def get_image(self, obj):
        """Extract image URL from dict if present."""
        if isinstance(obj, dict):
            return obj.get('image')
        return None


class RecommendedMenuItemSerializer(serializers.Serializer):
    """
    Serializer for recommended menu item data.
    
    Represents a menu item recommendation with category, pricing,
    popularity metrics, and personalization details.
    """
    
    id = serializers.IntegerField(
        help_text='Menu item ID'
    )
    name = serializers.CharField(
        max_length=255,
        help_text='Menu item name'
    )
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Item price'
    )
    category = serializers.CharField(
        max_length=10,
        help_text='Menu item category'
    )
    restaurant_id = serializers.IntegerField(
        help_text='Associated restaurant ID'
    )
    restaurant_name = serializers.CharField(
        max_length=255,
        help_text='Associated restaurant name'
    )
    average_rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=2,
        allow_null=True,
        help_text='Average rating from reviews (1.0-5.0 scale)'
    )
    image = serializers.SerializerMethodField(
        help_text='Menu item image URL'
    )
    distance_km = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        help_text='Distance from user in kilometers (if location filtering used)'
    )
    times_ordered = serializers.IntegerField(
        required=False,
        help_text='Number of times ordered (for popular items)'
    )
    trending_score = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        help_text='Popularity/trending score 0-100'
    )
    recommendation_reason = serializers.CharField(
        max_length=255,
        required=False,
        help_text='Explanation of why this item was recommended'
    )
    
    def get_image(self, obj):
        """Extract image URL from dict if present."""
        if isinstance(obj, dict):
            return obj.get('image')
        return None


class PopularItemCategoryFilterSerializer(serializers.Serializer):
    """
    Serializer for validating popular items category query parameters.
    """
    
    category = serializers.ChoiceField(
        choices=MenuItem.CATEGORY_CHOICES,
        required=True,
        help_text='Menu item category (required)'
    )
    lat = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        help_text='User latitude for location filtering (optional)'
    )
    lon = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        help_text='User longitude for location filtering (optional)'
    )
    radius = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=Decimal('10.0'),
        min_value=Decimal('0.1'),
        max_value=Decimal('50.0'),
        help_text='Search radius in kilometers (default: 10.0, max: 50.0)'
    )
    
    def validate(self, data):
        """Ensure both lat and lon are provided together."""
        lat = data.get('lat')
        lon = data.get('lon')
        
        if (lat is None and lon is not None) or (lat is not None and lon is None):
            raise serializers.ValidationError(
                'Both lat and lon must be provided together for location filtering'
            )
        
        return data


class PersonalizedRecommendationFilterSerializer(serializers.Serializer):
    """
    Serializer for validating personalized recommendation query parameters.
    """
    
    lat = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=True,
        help_text='User latitude (required)'
    )
    lon = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=True,
        help_text='User longitude (required)'
    )
    radius = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=Decimal('10.0'),
        min_value=Decimal('0.1'),
        max_value=Decimal('50.0'),
        help_text='Search radius in kilometers (default: 10.0, max: 50.0)'
    )


class RecommendationResponseSerializer(serializers.Serializer):
    """
    Serializer for recommendation API responses.
    
    Wraps the list of recommendations with metadata like count.
    """
    
    count = serializers.IntegerField(
        help_text='Number of recommendations returned'
    )
    data = serializers.ListField(
        child=serializers.DictField(),
        help_text='List of recommendations'
    )
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Optional message (e.g., when no results found)'
    )
