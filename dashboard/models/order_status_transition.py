from django.db import models
from order.models import Order


class OrderStatusTransition(models.Model):
    """Track order status changes for delivery time and distance analytics."""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='statustransitions')
    from_status = models.IntegerField()
    to_status = models.IntegerField()
    transitioned_at = models.DateTimeField(auto_now_add=True)
    driver_location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    driver_location_lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_backfilled = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'dashboard_order_status_transition'
        indexes = [
            models.Index(fields=['order', 'to_status']),
            models.Index(fields=['transitioned_at']),
        ]
        ordering = ['transitioned_at']
    
    def __str__(self):
        return f"Order {self.order_id}: {self.from_status}→{self.to_status}"
