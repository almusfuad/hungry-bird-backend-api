from django.urls import path
from recommendations.views.recommendation_views import (
    NearbyRestaurantsView,
    PopularItemsByCategoryView,
    PersonalizedRecommendationsView,
)

urlpatterns = [
    path('nearby-restaurants/', NearbyRestaurantsView.as_view(), name='nearby-restaurants'),
    path('popular-items/', PopularItemsByCategoryView.as_view(), name='popular-items'),
    path('personalized/', PersonalizedRecommendationsView.as_view(), name='personalized-recommendations'),
]
