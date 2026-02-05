from django.db import models
from django.conf import settings


class CSVExportLog(models.Model):
    """Log CSV exports for rate limiting (2 per hour per user)."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='csv_exports')
    exported_at = models.DateTimeField(auto_now_add=True)
    resource_type = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'dashboard_csv_export_log'
        indexes = [
            models.Index(fields=['user', 'exported_at']),
        ]
        ordering = ['-exported_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.resource_type}"
