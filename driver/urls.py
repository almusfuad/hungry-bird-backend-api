from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DriverProfileViewSet, DriverAvailabilityViewSet, DriverScheduleViewSet

router = DefaultRouter()

router.register(r'profile', DriverProfileViewSet, basename='driver-profile')
router.register(r'availability', DriverAvailabilityViewSet, basename='driver-availability')
router.register(r'schedule', DriverScheduleViewSet, basename='driver-schedule')

urlpatterns = [
    path('', include(router.urls)),
]
