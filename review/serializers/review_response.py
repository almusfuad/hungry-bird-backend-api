from rest_framework import serializers
from review.models import ReviewResponse, Review


class ReviewResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for ReviewResponse model.
    Handles restaurant owner responses to customer reviews.
    Responses are immutable once created.
    """
    owner_name = serializers.SerializerMethodField()
    review = serializers.PrimaryKeyRelatedField(
        queryset=Review.objects.filter(is_active=True),
        write_only=True
    )
    review_id = serializers.IntegerField(source='review.id', read_only=True)

    class Meta:
        model = ReviewResponse
        fields = [
            'id',
            'review',
            'review_id',
            'owner_name',
            'response_text',
            'created_at'
        ]
        read_only_fields = ['id', 'owner_name', 'created_at']

    def get_owner_name(self, obj):
        """
        Return restaurant name instead of owner username.
        """
        return obj.get_display_name()

    def validate(self, attrs):
        """
        Validate that:
        1. User is a restaurant owner (role=2)
        2. Owner matches the restaurant owner of the review
        3. Review is active
        4. Review doesn't already have a response
        """
        request = self.context.get('request')
        review = attrs.get('review')

        # Check user role
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({
                'detail': 'Authentication required.'
            })

        user_role = getattr(request.user, 'role', None)
        if user_role != 2:
            raise serializers.ValidationError({
                'detail': 'Only restaurant owners can respond to reviews.'
            })

        # Check if review belongs to user's restaurant
        if review.restaurant.owner != request.user:
            raise serializers.ValidationError({
                'review': 'You can only respond to reviews for your own restaurant.'
            })

        # Check if review is active
        if not review.is_active:
            raise serializers.ValidationError({
                'review': 'Cannot respond to an inactive review.'
            })

        # Check for duplicate response
        if hasattr(review, 'response'):
            raise serializers.ValidationError({
                'review': 'This review already has a response.'
            })

        return attrs
