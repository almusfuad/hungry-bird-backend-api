from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from dashboard.services import restaurant_dashboard
from dashboard.utils.export import check_export_rate_limit, export_to_csv, log_export
from dashboard.serializers.dashboard_serializers import DateRangeSerializer
from datetime import datetime, timedelta


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
        data = restaurant_dashboard.get_daily_orders(
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
        
        data = restaurant_dashboard.get_order_source_comparison(
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
        data = restaurant_dashboard.get_top_customers(
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
        data = restaurant_dashboard.get_popular_items(
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
        data = restaurant_dashboard.get_driver_performance(
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
