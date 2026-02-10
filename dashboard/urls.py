"""Dashboard URL configuration.

This module defines all dashboard API endpoints for restaurant owners,
drivers, customers, and platform administrators.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from dashboard.views.restaurant_views import (
    DailyOrdersView,
    OrderSourceComparisonView,
    TopCustomersView,
    PopularItemsView,
    DriverPerformanceView,
    PeriodComparisonView,
    PeakHoursAnalysisView,
    CustomerRetentionMetricsView,
    RevenueForecastView,
    DemandPatternsView,
)
from dashboard.views.customer_views import CustomerOverviewView
from dashboard.views.driver_views import (
    DriverOverviewView,
    DriverEfficiencyMetricsView,
    DriverEarningsBreakdownView,
    DriverPerformanceHistoryView,
    DriverPerformanceRankingView,
)
from dashboard.views.platform_views import PlatformDashboardViewSet

# Router for ViewSets
router = DefaultRouter()
router.register(r'platform', PlatformDashboardViewSet, basename='platform-dashboard')

urlpatterns = [
    # Platform Admin Dashboards (ViewSet routes)
    path('', include(router.urls)),
    
    # Restaurant Owner Dashboards
    path('restaurant/daily-orders/', DailyOrdersView.as_view(), name='restaurant-daily-orders'),
    path('restaurant/order-source/', OrderSourceComparisonView.as_view(), name='restaurant-order-source'),
    path('restaurant/top-customers/', TopCustomersView.as_view(), name='restaurant-top-customers'),
    path('restaurant/popular-items/', PopularItemsView.as_view(), name='restaurant-popular-items'),
    path('restaurant/driver-performance/', DriverPerformanceView.as_view(), name='restaurant-driver-performance'),
    
    # Restaurant Analytics (New)
    path('restaurant/period-comparison/', PeriodComparisonView.as_view(), name='restaurant-period-comparison'),
    path('restaurant/peak-hours/', PeakHoursAnalysisView.as_view(), name='restaurant-peak-hours'),
    path('restaurant/customer-retention/', CustomerRetentionMetricsView.as_view(), name='restaurant-customer-retention'),
    path('restaurant/revenue-forecast/', RevenueForecastView.as_view(), name='restaurant-revenue-forecast'),
    path('restaurant/demand-patterns/', DemandPatternsView.as_view(), name='restaurant-demand-patterns'),
    
    # Customer Dashboard
    path('customer/overview/', CustomerOverviewView.as_view(), name='customer-overview'),
    
    # Driver Dashboards
    path('driver/overview/', DriverOverviewView.as_view(), name='driver-overview'),
    path('driver/efficiency-metrics/', DriverEfficiencyMetricsView.as_view(), name='driver-efficiency-metrics'),
    path('driver/earnings-breakdown/', DriverEarningsBreakdownView.as_view(), name='driver-earnings-breakdown'),
    path('driver/performance-history/', DriverPerformanceHistoryView.as_view(), name='driver-performance-history'),
    path('driver/performance-ranking/', DriverPerformanceRankingView.as_view(), name='driver-performance-ranking'),
]

