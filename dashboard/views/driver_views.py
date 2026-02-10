"""Driver dashboard views.

This module provides API views for driver performance metrics and analytics.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from dashboard.services import driver
from dashboard.utils.export import check_export_rate_limit, export_to_csv, log_export
from dashboard.serializers.dashboard_serializers import DateRangeSerializer
from dashboard.serializers.forecasting_serializers import (
    DriverPerformanceRequestSerializer,
    DriverRankingRequestSerializer
)


class DriverOverviewView(APIView):
    """Get driver's delivery statistics and earnings."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 3:
            return Response({'error': 'Only drivers can access this'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        data = driver.get_driver_overview(
            request.user.id,
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end')
        )
        
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'driver_overview')
                # Convert single dict to list for CSV
                csv_data = [data]
                return export_to_csv(csv_data, 'driver_overview')
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        return Response(data, status=status.HTTP_200_OK)


class DriverEfficiencyMetricsView(APIView):
    """Get comprehensive driver efficiency metrics."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get driver efficiency metrics including acceptance rate, delivery speed, etc."""
        if request.user.role != 3:
            return Response(
                {'error': 'Only drivers can access this'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate request
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get efficiency metrics
        data = driver.get_driver_efficiency_metrics(
            driver_id=request.user.id,
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end')
        )
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class DriverEarningsBreakdownView(APIView):
    """Get driver earnings breakdown over time."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get earnings breakdown by day/week/month."""
        if request.user.role != 3:
            return Response(
                {'error': 'Only drivers can access this'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate request
        serializer = DriverPerformanceRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get earnings breakdown
        data = driver.get_driver_earnings_breakdown(
            driver_id=request.user.id,
            grouping=filters.get('grouping', 'weekly'),
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end'),
            limit=filters.get('limit', 12)
        )
        
        # Handle CSV export
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'driver_earnings_breakdown')
                return export_to_csv(data, 'driver_earnings_breakdown')
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class DriverPerformanceHistoryView(APIView):
    """Get driver performance metrics over time."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get performance history grouped by time period."""
        if request.user.role != 3:
            return Response(
                {'error': 'Only drivers can access this'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate request
        serializer = DriverPerformanceRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get performance history
        data = driver.get_driver_performance_history(
            driver_id=request.user.id,
            grouping=filters.get('grouping', 'weekly'),
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end'),
            limit=filters.get('limit', 12)
        )
        
        # Handle CSV export
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'driver_performance_history')
                return export_to_csv(data, 'driver_performance_history')
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
        
        return Response({'data': data}, status=status.HTTP_200_OK)


class DriverPerformanceRankingView(APIView):
    """Get ranked list of drivers by performance (admin or restaurant owner access)."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get driver performance rankings."""
        # Check permission - admin or restaurant owner
        if request.user.role not in [0, 2]:
            return Response(
                {'error': 'Only administrators and restaurant owners can access driver rankings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate request
        serializer = DriverRankingRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        # Get restaurant_id for restaurant owners
        restaurant_id = filters.get('restaurant_id')
        if request.user.role == 2:
            # Restaurant owner can only see their own drivers
            try:
                restaurant_id = request.user.restaurant.id
            except:
                return Response(
                    {'error': 'Restaurant not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get driver rankings
        data = driver.get_driver_performance_ranking(
            restaurant_id=restaurant_id,
            date_start=filters.get('date_start'),
            date_end=filters.get('date_end'),
            limit=filters.get('limit', 20)
        )
        
        # Handle CSV export
        if request.query_params.get('format') == 'csv':
            try:
                check_export_rate_limit(request.user)
                log_export(request.user, 'driver_performance_ranking')
                return export_to_csv(data, 'driver_performance_ranking')
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
        
        return Response({'data': data}, status=status.HTTP_200_OK)

