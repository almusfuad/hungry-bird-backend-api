"""Restaurant dashboard views.

This module provides API views for restaurant owner analytics and metrics.
"""

from datetime import datetime, timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from dashboard.services import restaurant
from dashboard.services import analytics
from dashboard.utils.export import check_export_rate_limit, export_to_csv, log_export
from dashboard.serializers.dashboard_serializers import DateRangeSerializer
from dashboard.serializers.forecasting_serializers import (
    ForecastRequestSerializer,
    GrowthRateRequestSerializer,
    DemandPatternsRequestSerializer
)


class DailyOrdersView(APIView):
    """Get daily order statistics for restaurant owners."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Check user is restaurant owner
        if request.user.role != 2:
            return Response({'error': 'Only restaurant owners can access this'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get restaurant
        try:
            restaurant = request.user.restaurant
        except:
            return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Parse filters
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        # Default to last 7 days
        filters = serializer.validated_data
        if not filters.get('date_start'):
            filters['date_start'] = datetime.now().date() - timedelta(days=7)
        if not filters.get('date_end'):
            filters['date_end'] = datetime.now().date()
        
        # Get data
        data = restaurant.get_daily_orders(
            restaurant.id,
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end'),
            order_source=filters.get('order_source')
        )
        
        # Check if CSV export requested
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'daily_orders')
                return export_to_csv(data, 'daily_orders')
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class OrderSourceComparisonView(APIView):
    """Compare POS vs Online orders."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 2:
            return Response({'error': 'Only restaurant owners can access this'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            restaurant = request.user.restaurant
        except:
            return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        data = restaurant.get_order_source_comparison(
            restaurant.id,
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end')
        )
        
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'order_source')
                return export_to_csv(data, 'order_source_comparison')
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class TopCustomersView(APIView):
    """Get top customers by spending."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 2:
            return Response({'error': 'Only restaurant owners can access this'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            restaurant = request.user.restaurant
        except:
            return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        limit = int(request.query_params.get('limit', 50))
        data = restaurant.get_top_customers(
            restaurant.id,
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end'),
            limit=limit
        )
        
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'top_customers')
                return export_to_csv(data, 'top_customers')
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class PopularItemsView(APIView):
    """Get most popular menu items."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 2:
            return Response({'error': 'Only restaurant owners can access this'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            restaurant = request.user.restaurant
        except:
            return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        limit = int(request.query_params.get('limit', 20))
        data = restaurant.get_popular_items(
            restaurant.id,
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end'),
            limit=limit
        )
        
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'popular_items')
                return export_to_csv(data, 'popular_items')
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class DriverPerformanceView(APIView):
    """Get driver delivery performance."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 2:
            return Response({'error': 'Only restaurant owners can access this'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            restaurant = request.user.restaurant
        except:
            return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        driver_id = request.query_params.get('driver_id')
        data = restaurant.get_driver_performance(
            restaurant.id,
            driver_id=driver_id,
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end')
        )
        
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'driver_performance')
                return export_to_csv(data, 'driver_performance')
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class PeriodComparisonView(APIView):
    """Compare current period metrics with previous period (MoM, WoW, YoY)."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get period-over-period comparison."""
        if request.user.role != 2:
            return Response(
                {'error': 'Only restaurant owners can access this'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            restaurant = request.user.restaurant
        except:
            return Response(
                {'error': 'Restaurant not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate request
        serializer = GrowthRateRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get period comparison
        data = restaurant.get_period_comparison(
            restaurant_id=restaurant.id,
            comparison_type=filters.get('comparison_type', 'mom'),
            current_period_start=filters.get('current_period_start'),
            current_period_end=filters.get('current_period_end')
        )
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class PeakHoursAnalysisView(APIView):
    """Analyze peak ordering hours and day-of-week patterns."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get peak hours and busiest days analysis."""
        if request.user.role != 2:
            return Response(
                {'error': 'Only restaurant owners can access this'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            restaurant = request.user.restaurant
        except:
            return Response(
                {'error': 'Restaurant not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate request
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get peak hours analysis
        data = restaurant.get_peak_hours_analysis(
            restaurant_id=restaurant.id,
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end')
        )
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class CustomerRetentionMetricsView(APIView):
    """Get customer retention and repeat customer metrics."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get customer retention metrics."""
        if request.user.role != 2:
            return Response(
                {'error': 'Only restaurant owners can access this'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            restaurant = request.user.restaurant
        except:
            return Response(
                {'error': 'Restaurant not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate request
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get retention metrics
        data = restaurant.get_customer_retention_metrics(
            restaurant_id=restaurant.id,
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end')
        )
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class RevenueForecastView(APIView):
    """Get revenue forecast for restaurant."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get revenue forecast using statistical methods."""
        if request.user.role != 2:
            return Response(
                {'error': 'Only restaurant owners can access this'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            restaurant = request.user.restaurant
        except:
            return Response(
                {'error': 'Restaurant not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate request
        serializer = ForecastRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get forecast
        data = analytics.forecast_revenue(
            restaurant_id=restaurant.id,
            periods_ahead=filters.get('periods_ahead', 7),
            method=filters.get('method', 'moving_average'),
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end')
        )
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class DemandPatternsView(APIView):
    """Analyze and predict demand patterns."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get demand patterns by day of week and hour."""
        if request.user.role != 2:
            return Response(
                {'error': 'Only restaurant owners can access this'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            restaurant = request.user.restaurant
        except:
            return Response(
                {'error': 'Restaurant not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate request
        serializer = DemandPatternsRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get demand patterns
        data = analytics.predict_demand_patterns(
            restaurant_id=restaurant.id,
            analysis_days=filters.get('analysis_days', 30)
        )
        
        return Response({'data': data}, status=status.HTTP_200_OK)
