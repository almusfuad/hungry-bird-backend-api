from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from review.models import ReviewResponse
from review.serializers import ReviewResponseSerializer
from hungryBird.permissions import IsRestaurantOwner
from notifications.dispatchers import ReviewNotificationDispatcher


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
        
        # Dispatch notification to customer
        transaction.on_commit(
            lambda: ReviewNotificationDispatcher.dispatch_review_response(instance)
        )
