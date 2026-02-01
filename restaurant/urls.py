from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RestaurantViewSet, MenuItemViewSet

router = DefaultRouter()

router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'menu_items', MenuItemViewSet, basename='menuitem')


urlpatterns = [
    path('', include(router.urls)),
    path('menu_items/update_add_on/<int:add_on_id>/', MenuItemViewSet.as_view({'patch': 'update_add_on'}), name='menuitem-update-add-on'),
    path('menu_items/delete_add_on/<int:add_on_id>/', MenuItemViewSet.as_view({'delete': 'delete_add_on'}), name='menuitem-delete-add-on'),
]