from django.db import models
from django.conf import settings


class CSVExportLog(models.Model):
    """
    Logs CSV export requests for rate limiting.
    
    This model tracks when users export dashboard data as CSV files.
    Used to enforce rate limiting (2 exports per hour per user) to prevent
    abuse and protect server resources.
    
    The logs are automatically cleaned up after 10 days by a Celery task
    to prevent unlimited table growth.
    
    Fields:
    - user: ForeignKey to User who requested the export
    - exported_at: Timestamp of export request
    - resource_type: Type of resource exported (e.g., 'daily_orders', 'customer_rankings')
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='csv_exports',
        help_text="User who requested the CSV export"
    )
    exported_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when CSV was exported"
    )
    resource_type = models.CharField(
        max_length=50,
        help_text="Type of dashboard resource exported (e.g., 'daily_orders', 'driver_performance')"
    )
    
    class Meta:
        db_table = 'dashboard_csv_export_log'
        indexes = [
            models.Index(fields=['user', 'exported_at'], name='idx_user_exported_at'),
        ]
        ordering = ['-exported_at']
        verbose_name = 'CSV Export Log'
        verbose_name_plural = 'CSV Export Logs'
    
    def __str__(self):
        return f"{self.user.username} exported {self.resource_type} at {self.exported_at}"
