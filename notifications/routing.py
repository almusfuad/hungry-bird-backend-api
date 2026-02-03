from django.urls import re_path
from notifications.consumers import DriverConsumer, RestaurantOwnerConsumer, CustomerConsumer


websocket_urlpatterns = [
    re_path(r'ws/driver/(?P<driver_id>\d+)/$', DriverConsumer.as_asgi()),
    re_path(r'ws/restaurant/(?P<restaurant_id>\d+)/$', RestaurantOwnerConsumer.as_asgi()),
    re_path(r'ws/customer/(?P<customer_id>\d+)/$', CustomerConsumer.as_asgi()),
]


