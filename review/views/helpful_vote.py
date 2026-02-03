from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from review.models import HelpfulVote
from review.serializers import HelpfulVoteSerializer


class HelpfulVoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing helpful votes on reviews.
    
    Permissions:
    - All actions: IsAuthenticated
    
    Features:
    - Users can vote on review helpfulness
    - Get or create pattern to handle duplicate votes
    - No update (use create to change vote)
    - Delete to remove vote
    """
    serializer_class = HelpfulVoteSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']  # No put, patch

    def get_queryset(self):
        """
        Filter votes to only those by the current user.
        """
        return HelpfulVote.objects.filter(
            user=self.request.user
        ).select_related('review', 'user')

    def create(self, request, *args, **kwargs):
        """
        Create or update a vote using get_or_create pattern.
        This handles duplicate votes gracefully by updating the existing vote.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        review = serializer.validated_data['review']
        is_helpful = serializer.validated_data.get('is_helpful', True)
        
        # Use update_or_create to handle duplicates
        vote, created = HelpfulVote.objects.update_or_create(
            review=review,
            user=request.user,
            defaults={'is_helpful': is_helpful}
        )
        
        # Return serialized vote
        output_serializer = self.get_serializer(vote)
        
        if created:
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(output_serializer.data, status=status.HTTP_200_OK)
