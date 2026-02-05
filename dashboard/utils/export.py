from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from dashboard.models import CSVExportLog
from rest_framework.exceptions import PermissionDenied
import csv
import io


def check_export_rate_limit(user, max_exports=2):
    """Check if user exceeded 2 exports per hour limit."""
    one_hour_ago = timezone.now() - timedelta(hours=1)
    count = CSVExportLog.objects.filter(user=user, exported_at__gte=one_hour_ago).count()
    
    if count >= max_exports:
        raise PermissionDenied(f"Export limit exceeded. Maximum {max_exports} exports per hour.")


def export_to_csv(data, filename='dashboard'):
    """Export list of dicts to CSV file."""
    if not data:
        output = io.StringIO()
        output.write('No data available\n')
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        return response
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    return response


def log_export(user, resource_type):
    """Log CSV export for rate limiting."""
    CSVExportLog.objects.create(user=user, resource_type=resource_type)
