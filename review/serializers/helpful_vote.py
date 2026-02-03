from rest_framework import serializers
from review.models import HelpfulVote, Review


class HelpfulVoteSerializer(serializers.ModelSerializer):
    """
    Serializer for HelpfulVote model.
    Handles voting on review helpfulness.
    """
    review = serializers.PrimaryKeyRelatedField(
        queryset=Review.objects.filter(is_active=True),
        write_only=True
    )
    review_id = serializers.IntegerField(source='review.id', read_only=True)

    class Meta:
        model = HelpfulVote
        fields = [
            'id',
            'review',
            'review_id',
            'user',
            'is_helpful',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']

    def validate(self, attrs):
        """
        Validate that:
        1. Review is active
        2. User is not voting on their own review
        """
        request = self.context.get('request')
        review = attrs.get('review')

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({
                'detail': 'Authentication required.'
            })

        # Check if review is active
        if not review.is_active:
            raise serializers.ValidationError({
                'review': 'Cannot vote on an inactive review.'
            })

        # Prevent self-voting
        if review.customer == request.user:
            raise serializers.ValidationError({
                'review': 'You cannot vote on your own review.'
            })

        return attrs
