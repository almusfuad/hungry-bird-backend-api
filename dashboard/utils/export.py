from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from dashboard.models import CSVExportLog
from rest_framework.exceptions import PermissionDenied, ValidationError
import csv
import io
import logging

logger = logging.getLogger(__name__)


def check_export_rate_limit(user, max_exports_per_hour=2):
    """
    Check if user has exceeded CSV export rate limit.
    
    Rate limit: maximum N exports per hour.
    
    Args:
        user: User instance
        max_exports_per_hour (int): Maximum exports allowed per hour (default: 2)
    
    Raises:
        PermissionDenied: If user has exceeded rate limit
    
    Example:
        >>> try:
        ...     check_export_rate_limit(request.user)
        ... except PermissionDenied as e:
        ...     return Response({'error': str(e)}, status=429)
    """
    one_hour_ago = timezone.now() - timedelta(hours=1)
    
    recent_exports = CSVExportLog.objects.filter(
        user=user,
        exported_at__gte=one_hour_ago
    ).count()
    
    if recent_exports >= max_exports_per_hour:
        remaining_time = CSVExportLog.objects.filter(
            user=user,
            exported_at__gte=one_hour_ago
        ).earliest('exported_at').exported_at + timedelta(hours=1)
        
        minutes_until_reset = int((remaining_time - timezone.now()).total_seconds() / 60)
        
        error_msg = f"Export rate limit exceeded. Maximum {max_exports_per_hour} exports per hour. Try again in {minutes_until_reset} minutes."
        logger.warning(f"Rate limit exceeded for user {user.id}: {recent_exports} exports in last hour")
        raise PermissionDenied(error_msg)


def validate_export_fields(requested_fields, available_fields):
    """
    Validate that requested export fields exist in available fields.
    
    Raises ValidationError with available fields list if invalid fields requested.
    
    Args:
        requested_fields (str or list): Comma-separated fields or list
                                       e.g., 'date,revenue,total_orders' or ['date', 'revenue']
        available_fields (dict): Available field mappings {db_field: display_name}
                                e.g., {'date': 'Date', 'revenue': 'Revenue'}
    
    Returns:
        list: Validated list of field names
    
    Raises:
        ValidationError: If invalid fields or no fields requested
    
    Example:
        >>> available = {'date': 'Date', 'revenue': 'Revenue', 'total_orders': 'Total Orders'}
        >>> fields = validate_export_fields('date,revenue', available)
        >>> print(fields)
        ['date', 'revenue']
    """
    
    # Parse requested fields
    if isinstance(requested_fields, str):
        requested = [f.strip() for f in requested_fields.split(',') if f.strip()]
    else:
        requested = requested_fields or []
    
    # If no fields specified, use all available
    if not requested:
        return list(available_fields.keys())
    
    # Validate each requested field
    invalid_fields = [f for f in requested if f not in available_fields]
    
    if invalid_fields:
        error_msg = f"Invalid fields: {', '.join(invalid_fields)}. Available fields: {', '.join(available_fields.keys())}"
        logger.warning(f"Invalid export fields requested: {invalid_fields}")
        raise ValidationError(error_msg)
    
    return requested


def export_to_csv(data, field_mapping, requested_fields=None):
    """
    Export dashboard data to CSV format with optional field selection.
    
    Creates CSV response with proper headers and content disposition for download.
    Logs export for rate limiting purposes.
    
    Args:
        data (list): List of dict rows to export
        field_mapping (dict): Field name to display name mapping
                             {db_field: display_name}
        requested_fields (str or list, optional): Fields to include
                                                 If None, includes all fields
    
    Returns:
        HttpResponse: CSV file download response
    
    Example:
        >>> data = [
        ...     {'date': '2025-01-01', 'revenue': 1000.50, 'total_orders': 10},
        ...     {'date': '2025-01-02', 'revenue': 1200.75, 'total_orders': 12},
        ... ]
        >>> field_mapping = {'date': 'Date', 'revenue': 'Revenue', 'total_orders': 'Total Orders'}
        >>> response = export_to_csv(data, field_mapping, 'date,revenue')
    """
    
    # Validate fields
    export_fields = validate_export_fields(requested_fields, field_mapping)
    
    # Create CSV in memory
    output = io.StringIO()
    
    # Get display names for headers
    headers = [field_mapping[f] for f in export_fields]
    
    # Write CSV
    writer = csv.writer(output)
    writer.writerow(headers)
    
    # Write data rows
    for row in data:
        values = [row.get(f, '') for f in export_fields]
        writer.writerow(values)
    
    # Create HTTP response
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="dashboard_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    logger.info(f"CSV export created with {len(data)} rows and {len(export_fields)} fields")
    
    return response


def log_csv_export(user, resource_type):
    """
    Log CSV export for rate limiting.
    
    Args:
        user: User who exported the CSV
        resource_type (str): Type of resource exported (e.g., 'daily_orders')
    """
    CSVExportLog.objects.create(user=user, resource_type=resource_type)
    logger.info(f"Logged CSV export for user {user.id}: {resource_type}")
