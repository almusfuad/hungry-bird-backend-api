from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q
from django.db import transaction
from decimal import Decimal

from review.models import Review
from review.serializers import ReviewSerializer
from hungryBird.permissions import IsCustomer
from notifications.dispatcher import dispatch_notification


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing customer reviews.
    
    Permissions:
    - create, update, partial_update, destroy: IsCustomer
    - list, retrieve: AllowAny
    
    Features:
    - Role-based queryset filtering
    - Query parameter filtering (rating, restaurant, menu_item, is_anonymous)
    - Sorting by helpful votes or creation date
    - Soft delete on destroy
    - Notification dispatch on create
    - Custom actions: aggregate_ratings, rating_breakdown
    """
    serializer_class = ReviewSerializer

    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsCustomer()]
        elif self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [AllowAny()]

    def get_queryset(self):
        """
        Get queryset with role-based filtering and query parameter filters.
        """
        user = self.request.user
        queryset = Review.objects.all()

        # Role-based filtering
        if user.is_authenticated:
            user_role = getattr(user, 'role', None)
            if user_role == 1:  # Customer - see their own reviews
                queryset = queryset.filter(customer=user)
            elif user_role == 2:  # Restaurant Owner - see their restaurant reviews
                queryset = queryset.filter(restaurant__owner=user)
            else:  # Others - see only active reviews
                queryset = queryset.filter(is_active=True)
        else:
            # Unauthenticated users see only active reviews
            queryset = queryset.filter(is_active=True)

        # Query parameter filters
        min_rating = self.request.query_params.get('min_rating')
        max_rating = self.request.query_params.get('max_rating')
        restaurant_id = self.request.query_params.get('restaurant_id')
        menu_item_id = self.request.query_params.get('menu_item_id')
        is_anonymous = self.request.query_params.get('is_anonymous')
        ordering = self.request.query_params.get('ordering', '-created_at')

        # Rating filters
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=Decimal(min_rating))
            except (ValueError, TypeError):
                pass

        if max_rating:
            try:
                queryset = queryset.filter(rating__lte=Decimal(max_rating))
            except (ValueError, TypeError):
                pass

        # Restaurant filter
        if restaurant_id:
            try:
                queryset = queryset.filter(restaurant_id=int(restaurant_id))
            except (ValueError, TypeError):
                pass

        # Menu item filter
        if menu_item_id:
            try:
                queryset = queryset.filter(menu_item_id=int(menu_item_id))
            except (ValueError, TypeError):
                pass

        # Anonymous filter
        if is_anonymous:
            if is_anonymous.lower() == 'true':
                queryset = queryset.filter(is_anonymous=True)
            elif is_anonymous.lower() == 'false':
                queryset = queryset.filter(is_anonymous=False)

        # Annotate with helpful count for sorting
        queryset = queryset.annotate(
            helpful_count=Count(
                'helpful_votes',
                filter=Q(helpful_votes__is_helpful=True)
            )
        )

        # Ordering
        if ordering == 'helpful':
            queryset = queryset.order_by('-helpful_count', '-created_at')
        else:
            queryset = queryset.order_by('-created_at')

        # Optimize queries
        queryset = queryset.select_related(
            'customer',
            'restaurant',
            'menu_item',
            'order'
        ).prefetch_related('response', 'helpful_votes')

        return queryset

    def perform_create(self, serializer):
        """
        Create review and dispatch notification to restaurant owner.
        """
        instance = serializer.save(customer=self.request.user)
        
        # Dispatch notification if owner has notifications enabled
        def send_notification():
            if instance.restaurant.owner and instance.restaurant.owner.enable_review_notifications:
                dispatch_notification(
                    type='new_review',
                    recipient=instance.restaurant.owner,
                    data={
                        'message': f'New review received for {instance.menu_item.name if instance.menu_item else instance.restaurant.name}',
                        'review_id': instance.id,
                        'restaurant_id': instance.restaurant.id,
                        'menu_item_id': instance.menu_item.id if instance.menu_item else None,
                        'rating': str(instance.rating),
                        'customer_name': instance.get_display_name()
                    }
                )
        
        transaction.on_commit(send_notification)

    def perform_destroy(self, instance):
        """
        Soft delete - set is_active to False instead of deleting.
        """
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=['get'], url_path='aggregate-ratings', permission_classes=[AllowAny])
    def aggregate_ratings(self, request):
        """
        Get aggregate ratings for a restaurant or menu item.
        
        Query params:
        - restaurant_id: Get restaurant-level ratings
        - menu_item_id: Get menu item ratings
        
        Returns:
        {
            "average_rating": 4.25,
            "total_reviews": 150
        }
        """
        restaurant_id = request.query_params.get('restaurant_id')
        menu_item_id = request.query_params.get('menu_item_id')

        if not restaurant_id and not menu_item_id:
            return Response(
                {'error': 'Either restaurant_id or menu_item_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if menu_item_id:
                from restaurant.models import MenuItem
                menu_item = MenuItem.objects.get(id=int(menu_item_id))
                avg_rating = menu_item.get_average_rating()
                total_reviews = menu_item.get_total_reviews()
            else:
                from restaurant.models import Restaurant
                restaurant = Restaurant.objects.get(id=int(restaurant_id))
                avg_rating = restaurant.get_average_rating()
                total_reviews = restaurant.get_total_reviews()

            return Response({
                'average_rating': float(round(Decimal(str(avg_rating)) if avg_rating else Decimal('0.00'), 2)),
                'total_reviews': total_reviews
            })

        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid ID provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='rating-breakdown', permission_classes=[AllowAny])
    def rating_breakdown(self, request):
        """
        Get rating breakdown showing count for each rating level.
        
        Query params:
        - restaurant_id: Get restaurant rating breakdown
        - menu_item_id: Get menu item rating breakdown
        
        Returns:
        {
            "breakdown": {
                "5": 50,
                "4": 30,
                "3": 15,
                "2": 3,
                "1": 2
            },
            "total_reviews": 100
        }
        """
        restaurant_id = request.query_params.get('restaurant_id')
        menu_item_id = request.query_params.get('menu_item_id')

        if not restaurant_id and not menu_item_id:
            return Response(
                {'error': 'Either restaurant_id or menu_item_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if menu_item_id:
                from restaurant.models import MenuItem
                menu_item = MenuItem.objects.get(id=int(menu_item_id))
                breakdown = menu_item.get_rating_breakdown()
                total_reviews = menu_item.get_total_reviews()
            else:
                from restaurant.models import Restaurant
                restaurant = Restaurant.objects.get(id=int(restaurant_id))
                breakdown = restaurant.get_rating_breakdown()
                total_reviews = restaurant.get_total_reviews()

            # Convert keys to strings for JSON serialization
            breakdown_str = {str(k): v for k, v in breakdown.items()}

            return Response({
                'breakdown': breakdown_str,
                'total_reviews': total_reviews
            })

        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid ID provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
