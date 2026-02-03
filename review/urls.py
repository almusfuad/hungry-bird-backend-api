from django.urls import path
from rest_framework.routers import DefaultRouter
from review.views import ReviewViewSet, ReviewResponseViewSet, HelpfulVoteViewSet

router = DefaultRouter()

# Register ViewSets
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'review-responses', ReviewResponseViewSet, basename='review-response')
router.register(r'helpful-votes', HelpfulVoteViewSet, basename='helpful-vote')

urlpatterns = router.urls
