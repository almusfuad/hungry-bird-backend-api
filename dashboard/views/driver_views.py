from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from dashboard.services import driver_dashboard
from dashboard.utils.export import check_export_rate_limit, export_to_csv, log_export
from dashboard.serializers.dashboard_serializers import DateRangeSerializer


class DriverOverviewView(APIView):
    """Get driver's delivery statistics and earnings."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 3:
            return Response({'error': 'Only drivers can access this'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = DateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        
        data = driver_dashboard.get_driver_overview(
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
