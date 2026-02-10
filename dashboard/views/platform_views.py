"""Platform-wide dashboard views for admin users.

This module provides ViewSet with custom actions for platform-level
analytics, accessible only to admin users (role=0).
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from dashboard.services import platform
from dashboard.services import analytics
from dashboard.serializers.forecasting_serializers import (
    PlatformStatsRequestSerializer,
    TrendRequestSerializer,
    TopItemsRequestSerializer,
    RestaurantRankingRequestSerializer,
    ForecastRequestSerializer,
    GrowthRateRequestSerializer,
)
from dashboard.serializers.dashboard_serializers import DashboardResponseSerializer
from dashboard.utils.export import check_export_rate_limit, log_export, export_to_csv


class PlatformDashboardViewSet(ViewSet):
    """Platform-wide analytics for admin users."""
    
    permission_classes = [IsAuthenticated]
    
    def _check_admin_permission(self, request):
        """Check if user is admin (role=0)."""
        if request.user.role != 0:
            return Response(
                {'error': 'Only administrators can access platform-wide analytics'},
                status=status.HTTP_403_FORBIDDEN
            )
        return None
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get platform-wide revenue statistics including total revenue, "
                            "order counts, payment method breakdown, and completion rates.",
        query_serializer=PlatformStatsRequestSerializer,
        responses={
            200: openapi.Response('Platform revenue statistics', DashboardResponseSerializer),
            403: 'Forbidden - Admin access required'
        }
    )
    @action(detail=False, methods=['get'], url_path='revenue-stats')
    def revenue_stats(self, request):
        """Get platform-wide revenue statistics.
        
        Query Parameters:
            - date_start: Start date (YYYY-MM-DD)
            - date_end: End date (YYYY-MM-DD)
            - order_source: Filter by order source (1=Online, 2=POS)
        """
        # Check admin permission
        permission_error = self._check_admin_permission(request)
        if permission_error:
            return permission_error
        
        # Validate request
        serializer = PlatformStatsRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get revenue stats
        data = platform.get_platform_revenue_stats(
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end'),
            order_source=filters.get('order_source')
        )
        
        return Response({'data': data}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get order volume and revenue trends over time with "
                            "customizable grouping (hourly, daily, weekly, monthly).",
        query_serializer=TrendRequestSerializer,
        responses={
            200: openapi.Response('Order trends data', DashboardResponseSerializer),
            403: 'Forbidden - Admin access required'
        }
    )
    @action(detail=False, methods=['get'], url_path='order-trends')
    def order_trends(self, request):
        """Get order volume and revenue trends.
        
        Query Parameters:
            - grouping: Time grouping (hourly/daily/weekly/monthly)
            - date_start: Start date
            - date_end: End date
            - limit: Max periods to return (default: 30)
            - format: Response format (json/csv)
        """
        # Check admin permission
        permission_error = self._check_admin_permission(request)
        if permission_error:
            return permission_error
        
        # Validate request
        serializer = TrendRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get trend data
        data = platform.get_order_trends(
            grouping=filters.get('grouping', 'daily'),
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end'),
            limit=filters.get('limit', 30)
        )
        
        # Handle CSV export
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'platform_order_trends')
                return export_to_csv(data, 'platform_order_trends')
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
        
        return Response({'data': data}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get trending menu items across all restaurants with "
                            "popularity metrics, revenue, and velocity indicators.",
        query_serializer=TopItemsRequestSerializer,
        responses={
            200: openapi.Response('Trending items', DashboardResponseSerializer),
            403: 'Forbidden - Admin access required'
        }
    )
    @action(detail=False, methods=['get'], url_path='trending-items')
    def trending_items(self, request):
        """Get trending menu items platform-wide.
        
        Query Parameters:
            - date_start: Start date
            - date_end: End date
            - limit: Max items to return (default: 50)
            - format: Response format (json/csv)
        """
        # Check admin permission
        permission_error = self._check_admin_permission(request)
        if permission_error:
            return permission_error
        
        # Validate request
        serializer = TopItemsRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get trending items
        data = platform.get_trending_items(
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end'),
            limit=filters.get('limit', 50)
        )
        
        # Handle CSV export
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'trending_items')
                return export_to_csv(data, 'trending_items')
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
        
        return Response({'data': data}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get top performing restaurants ranked by revenue and performance metrics.",
        query_serializer=RestaurantRankingRequestSerializer,
        responses={
            200: openapi.Response('Top restaurants', DashboardResponseSerializer),
            403: 'Forbidden - Admin access required'
        }
    )
    @action(detail=False, methods=['get'], url_path='top-restaurants')
    def top_restaurants(self, request):
        """Get top performing restaurants.
        
        Query Parameters:
            - date_start: Start date
            - date_end: End date
            - limit: Max restaurants to return (default: 20)
            - format: Response format (json/csv)
        """
        # Check admin permission
        permission_error = self._check_admin_permission(request)
        if permission_error:
            return permission_error
        
        # Validate request
        serializer = RestaurantRankingRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get top restaurants
        data = platform.get_top_restaurants(
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end'),
            limit=filters.get('limit', 20)
        )
        
        # Handle CSV export
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'top_restaurants')
                return export_to_csv(data, 'top_restaurants')
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
        
        return Response({'data': data}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Get platform-wide customer metrics including acquisition, "
                            "retention, and engagement statistics.",
        query_serializer=PlatformStatsRequestSerializer,
        responses={
            200: openapi.Response('Customer metrics', DashboardResponseSerializer),
            403: 'Forbidden - Admin access required'
        }
    )
    @action(detail=False, methods=['get'], url_path='customer-metrics')
    def customer_metrics(self, request):
        """Get platform-wide customer metrics.
        
        Query Parameters:
            - date_start: Start date
            - date_end: End date
        """
        # Check admin permission
        permission_error = self._check_admin_permission(request)
        if permission_error:
            return permission_error
        
        # Validate request
        serializer = PlatformStatsRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get customer metrics
        data = platform.get_customer_metrics(
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end')
        )
        
        return Response({'data': data}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Forecast platform-wide revenue using statistical methods.",
        query_serializer=ForecastRequestSerializer,
        responses={
            200: openapi.Response('Revenue forecast', DashboardResponseSerializer),
            403: 'Forbidden - Admin access required'
        }
    )
    @action(detail=False, methods=['get'], url_path='revenue-forecast')
    def revenue_forecast(self, request):
        """Get platform-wide revenue forecast.
        
        Query Parameters:
            - periods_ahead: Days to forecast (1-90, default: 7)
            - method: Forecasting method (moving_average/exponential_smoothing/linear_trend)
            - date_start: Historical data start date
            - date_end: Historical data end date
        """
        # Check admin permission
        permission_error = self._check_admin_permission(request)
        if permission_error:
            return permission_error
        
        # Validate request
        serializer = ForecastRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get forecast
        data = analytics.forecast_revenue(
            restaurant_id=None,  # Platform-wide
            periods_ahead=filters.get('periods_ahead', 7),
            method=filters.get('method', 'moving_average'),
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end')
        )
        
        return Response({'data': data}, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        method='get',
        operation_description="Calculate platform-wide growth rates with period-over-period comparison.",
        query_serializer=GrowthRateRequestSerializer,
        responses={
            200: openapi.Response('Growth rates', DashboardResponseSerializer),
            403: 'Forbidden - Admin access required'
        }
    )
    @action(detail=False, methods=['get'], url_path='growth-rates')
    def growth_rates(self, request):
        """Get platform-wide growth rates.
        
        Query Parameters:
            - comparison_type: Comparison type (mom/wow/yoy)
            - current_period_start: Current period start date
            - current_period_end: Current period end date
        """
        # Check admin permission
        permission_error = self._check_admin_permission(request)
        if permission_error:
            return permission_error
        
        # Validate request
        serializer = GrowthRateRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get growth rates
        data = analytics.calculate_growth_rate(
            restaurant_id=None,  # Platform-wide
            comparison_type=filters.get('comparison_type', 'mom'),
            current_period_start=filters.get('current_period_start'),
            current_period_end=filters.get('current_period_end')
        )
        
        return Response({'data': data}, status=status.HTTP_200_OK)
