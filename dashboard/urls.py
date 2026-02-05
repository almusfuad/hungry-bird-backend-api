from django.urls import path
from dashboard.views.restaurant_views import (
    DailyOrdersView,
    OrderSourceComparisonView,
    TopCustomersView,
    PopularItemsView,
    DriverPerformanceView
)
from dashboard.views.customer_views import CustomerOverviewView
from dashboard.views.driver_views import DriverOverviewView

urlpatterns = [
    # Restaurant Owner Dashboards
    path('restaurant/daily-orders/', DailyOrdersView.as_view(), name='restaurant-daily-orders'),
    path('restaurant/order-source/', OrderSourceComparisonView.as_view(), name='restaurant-order-source'),
    path('restaurant/top-customers/', TopCustomersView.as_view(), name='restaurant-top-customers'),
    path('restaurant/popular-items/', PopularItemsView.as_view(), name='restaurant-popular-items'),
    path('restaurant/driver-performance/', DriverPerformanceView.as_view(), name='restaurant-driver-performance'),
    
    # Customer Dashboard
    path('customer/overview/', CustomerOverviewView.as_view(), name='customer-overview'),
    
    # Driver Dashboard
    path('driver/overview/', DriverOverviewView.as_view(), name='driver-overview'),
]
