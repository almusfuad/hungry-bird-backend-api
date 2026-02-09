"""
API Views for Recommendations Engine

Provides REST API endpoints for:
1. Nearby restaurants based on user location
2. Popular items by category
3. Personalized recommendations for authenticated users
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from recommendations.services import recommendation_engine, content_filtering
from recommendations.models import RecommendationLog
from hungryBird.permissions import IsCustomer


class NearbyRestaurantsView(APIView):
    """
    Get restaurants near a user's location.
    
    Supports optional filtering by category and minimum rating.
    Results sorted by distance (nearest first) then popularity.
    
    Query Parameters:
        - lat (float, required): User's latitude
        - lon (float, required): User's longitude
        - radius (float, optional): Search radius in km (default: 10.0, max: 50.0)
        - category (str, optional): MenuItem category filter
        - min_rating (float, optional): Minimum average rating filter (1.0-5.0)
    
    Response:
        List of restaurants with:
            - id, name, address, latitude, longitude
            - distance_km: Distance from user
            - order_count: Number of completed orders
            - average_rating: Average rating from reviews
            - image: Restaurant image URL
    """
    
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description='Get nearby restaurants based on user location',
        manual_parameters=[
            openapi.Parameter(
                'lat',
                openapi.IN_QUERY,
                description='User latitude (required)',
                type=openapi.TYPE_NUMBER,
                required=True
            ),
            openapi.Parameter(
                'lon',
                openapi.IN_QUERY,
                description='User longitude (required)',
                type=openapi.TYPE_NUMBER,
                required=True
            ),
            openapi.Parameter(
                'radius',
                openapi.IN_QUERY,
                description='Search radius in kilometers (default: 10.0, max: 50.0)',
                type=openapi.TYPE_NUMBER,
                default=10.0
            ),
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description='Optional category filter',
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'min_rating',
                openapi.IN_QUERY,
                description='Minimum average rating filter (1.0-5.0)',
                type=openapi.TYPE_NUMBER
            ),
        ],
        responses={
            200: openapi.Response(
                description='List of nearby restaurants',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'distance_km': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'average_rating': openapi.Schema(type=openapi.TYPE_NUMBER),
                                }
                            )
                        ),
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            400: 'Invalid query parameters'
        }
    )
    def get(self, request):
        """Get nearby restaurants based on location."""
        try:
            # Validate required parameters
            lat = request.query_params.get('lat')
            lon = request.query_params.get('lon')
            
            if not lat or not lon:
                return Response(
                    {'error': 'Both lat and lon parameters are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse parameters
            try:
                lat = float(lat)
                lon = float(lon)
            except ValueError:
                return Response(
                    {'error': 'lat and lon must be valid numbers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Optional parameters
            radius = request.query_params.get('radius', 10.0)
            try:
                radius = float(radius)
                # Clamp radius to max 50km
                radius = min(radius, 50.0)
            except ValueError:
                return Response(
                    {'error': 'radius must be a valid number'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            category = request.query_params.get('category')
            min_rating = request.query_params.get('min_rating')
            
            if min_rating:
                try:
                    min_rating = float(min_rating)
                except ValueError:
                    return Response(
                        {'error': 'min_rating must be a valid number'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get recommendations
            restaurants = recommendation_engine.get_nearby_restaurants(
                lat=lat,
                lon=lon,
                radius_km=radius,
                category=category,
                min_rating=min_rating,
                limit=10
            )
            
            # Log recommendations for analytics
            for restaurant in restaurants:
                RecommendationLog.objects.create(
                    customer=request.user if request.user.is_authenticated else None,
                    recommendation_type=RecommendationLog.NEARBY_RESTAURANT,
                    restaurant_id=restaurant['id'],
                    user_latitude=lat,
                    user_longitude=lon,
                    search_radius=radius,
                    was_clicked=False
                )
            
            return Response(
                {
                    'count': len(restaurants),
                    'data': restaurants
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PopularItemsByCategoryView(APIView):
    """
    Get popular menu items by category.
    
    Optionally filters by location (latitude, longitude, radius).
    Returns items ordered at least 5 times, sorted by order frequency.
    
    Query Parameters:
        - category (str, required): MenuItem category
        - lat (float, optional): User latitude for location filtering
        - lon (float, optional): User longitude for location filtering
        - radius (float, optional): Search radius in km (default: 10.0, max: 50.0)
    
    Response:
        List of menu items with:
            - id, name, price, category
            - restaurant_id, restaurant_name
            - times_ordered: Number of times ordered
            - average_rating: Average rating from reviews
            - image: Item image URL
            - distance_km: Distance from user (if location provided)
    """
    
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description='Get popular menu items by category',
        manual_parameters=[
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description='MenuItem category (required)',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'lat',
                openapi.IN_QUERY,
                description='User latitude for location filtering (optional)',
                type=openapi.TYPE_NUMBER
            ),
            openapi.Parameter(
                'lon',
                openapi.IN_QUERY,
                description='User longitude for location filtering (optional)',
                type=openapi.TYPE_NUMBER
            ),
            openapi.Parameter(
                'radius',
                openapi.IN_QUERY,
                description='Search radius in kilometers (default: 10.0, max: 50.0)',
                type=openapi.TYPE_NUMBER,
                default=10.0
            ),
        ],
        responses={
            200: 'List of popular items',
            400: 'Invalid category or parameters'
        }
    )
    def get(self, request):
        """Get popular menu items by category."""
        try:
            category = request.query_params.get('category')
            
            if not category:
                return Response(
                    {'error': 'category parameter is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Optional location parameters
            lat = request.query_params.get('lat')
            lon = request.query_params.get('lon')
            radius = request.query_params.get('radius', 10.0)
            
            if lat and lon:
                try:
                    lat = float(lat)
                    lon = float(lon)
                except ValueError:
                    return Response(
                        {'error': 'lat and lon must be valid numbers'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    radius = float(radius)
                    radius = min(radius, 50.0)
                except ValueError:
                    return Response(
                        {'error': 'radius must be a valid number'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                lat = None
                lon = None
            
            # Get recommendations
            items = recommendation_engine.get_popular_items_by_category(
                category=category,
                lat=lat,
                lon=lon,
                radius_km=radius if lat and lon else 10.0,
                limit=10
            )
            
            if not items:
                return Response(
                    {
                        'count': 0,
                        'data': [],
                        'message': f'No popular items found for category: {category}'
                    },
                    status=status.HTTP_200_OK
                )
            
            # Log recommendations
            for item in items:
                RecommendationLog.objects.create(
                    customer=request.user if request.user.is_authenticated else None,
                    recommendation_type=RecommendationLog.POPULAR_ITEM,
                    menu_item_id=item['id'],
                    user_latitude=lat if lat else 0,
                    user_longitude=lon if lon else 0,
                    search_radius=radius if lat and lon else 10.0,
                    was_clicked=False
                )
            
            return Response(
                {
                    'count': len(items),
                    'data': items
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PersonalizedRecommendationsView(APIView):
    """
    Get personalized recommendations for authenticated customer.
    
    Analyzes user's order history to identify preferred categories and restaurants.
    Returns 70% items from preferred categories + 30% discovery items (highly-rated
    from other categories) to balance preference and discovery.
    
    If user has no order history, falls back to trending nearby items.
    
    Query Parameters:
        - lat (float, required): User latitude
        - lon (float, required): User longitude
        - radius (float, optional): Search radius in km (default: 10.0, max: 50.0)
    
    Response:
        List of personalized recommendations with:
            - id, name, price, category
            - restaurant_id, restaurant_name
            - average_rating: Average rating from reviews
            - image: Item image URL
            - distance_km: Distance from user
            - recommendation_reason: Why this item was recommended
    """
    
    permission_classes = [IsAuthenticated, IsCustomer]
    
    @swagger_auto_schema(
        operation_description='Get personalized recommendations for authenticated customer',
        manual_parameters=[
            openapi.Parameter(
                'lat',
                openapi.IN_QUERY,
                description='User latitude (required)',
                type=openapi.TYPE_NUMBER,
                required=True
            ),
            openapi.Parameter(
                'lon',
                openapi.IN_QUERY,
                description='User longitude (required)',
                type=openapi.TYPE_NUMBER,
                required=True
            ),
            openapi.Parameter(
                'radius',
                openapi.IN_QUERY,
                description='Search radius in kilometers (default: 10.0, max: 50.0)',
                type=openapi.TYPE_NUMBER,
                default=10.0
            ),
        ],
        responses={
            200: 'List of personalized recommendations',
            400: 'Invalid parameters or user not authenticated',
            403: 'User is not a customer'
        }
    )
    def get(self, request):
        """Get personalized recommendations for the authenticated user."""
        try:
            # Validate required parameters
            lat = request.query_params.get('lat')
            lon = request.query_params.get('lon')
            
            if not lat or not lon:
                return Response(
                    {'error': 'Both lat and lon parameters are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse parameters
            try:
                lat = float(lat)
                lon = float(lon)
            except ValueError:
                return Response(
                    {'error': 'lat and lon must be valid numbers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Optional radius parameter
            radius = request.query_params.get('radius', 10.0)
            try:
                radius = float(radius)
                radius = min(radius, 50.0)
            except ValueError:
                return Response(
                    {'error': 'radius must be a valid number'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get personalized recommendations
            recommendations = content_filtering.get_personalized_recommendations(
                user_id=request.user.id,
                lat=lat,
                lon=lon,
                radius_km=radius,
                limit=10
            )
            
            # Log recommendations
            for item in recommendations:
                RecommendationLog.objects.create(
                    customer=request.user,
                    recommendation_type=RecommendationLog.PERSONALIZED,
                    menu_item_id=item['id'],
                    user_latitude=lat,
                    user_longitude=lon,
                    search_radius=radius,
                    was_clicked=False
                )
            
            return Response(
                {
                    'count': len(recommendations),
                    'data': recommendations
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
