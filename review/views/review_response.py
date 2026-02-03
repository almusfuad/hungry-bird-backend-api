from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from review.models import ReviewResponse
from review.serializers import ReviewResponseSerializer
from hungryBird.permissions import IsRestaurantOwner
from notifications.dispatcher import dispatch_notification


class ReviewResponseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing restaurant owner responses to reviews.
    
    Permissions:
    - All actions: IsAuthenticated + IsRestaurantOwner
    
    Features:
    - Immutable responses (no update/delete via http_method_names)
    - Notification dispatch to customer on create
    - Filtered to owner's restaurants
    """
    serializer_class = ReviewResponseSerializer
    permission_classes = [IsAuthenticated, IsRestaurantOwner]
    http_method_names = ['get', 'post', 'head', 'options']  # No put, patch, delete

    def get_queryset(self):
        """
        Filter responses to only those for reviews of the owner's restaurant.
        """
        return ReviewResponse.objects.filter(
            review__restaurant__owner=self.request.user
        ).select_related(
            'review__customer',
            'review__restaurant',
            'review__menu_item',
            'owner'
        )

    def perform_create(self, serializer):
        """
        Create response and dispatch notification to customer.
        """
        instance = serializer.save(owner=self.request.user)
        
        # Dispatch notification if customer has notifications enabled
        def send_notification():
            if instance.review.customer and instance.review.customer.enable_review_notifications:
                dispatch_notification(
                    type='review_response',
                    recipient=instance.review.customer,
                    data={
                        'message': f'{instance.review.restaurant.name} responded to your review',
                        'review_id': instance.review.id,
                        'restaurant_id': instance.review.restaurant.id,
                        'restaurant_name': instance.review.restaurant.name,
                        'menu_item_id': instance.review.menu_item.id if instance.review.menu_item else None
                    }
                )
        
        transaction.on_commit(send_notification)
