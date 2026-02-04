from django.urls import path, include
from rest_framework.routers import DefaultRouter
from subscriptions.views import UserSubscriptionViewSet, SubscriptionPlanViewSet

router = DefaultRouter()
router.register(r'subscriptions', UserSubscriptionViewSet, basename='subscription')
router.register(r'plans', SubscriptionPlanViewSet, basename='subscription-plan')

urlpatterns = [
    path('', include(router.urls)),
]
