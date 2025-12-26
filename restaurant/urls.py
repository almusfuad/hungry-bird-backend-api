from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RestaurantViewSet, MenuItemViewSet

router = DefaultRouter()

router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'menu_items', MenuItemViewSet, basename='menuitem')


urlpatterns = [
    path('', include(router.urls)),
]