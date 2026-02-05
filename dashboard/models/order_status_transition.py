from django.db import models
from order.models import Order


class OrderStatusTransition(models.Model):
    """
    Tracks status transitions for orders with timestamps and driver location.
    
    This model captures when an order changes from one status to another,
    including the driver's location at the time of transition. This enables
    accurate delivery time and distance calculations for driver performance analytics.
    
    For online orders, the critical transitions are:
    - to_status=4 (Out for Delivery): Captures pickup location
    - to_status=5 (Delivered): Captures delivery completion time
    
    Fields:
    - order: ForeignKey to Order
    - from_status: Previous order status
    - to_status: New order status
    - transitioned_at: Timestamp of status change
    - driver_location_lat: Driver's latitude at transition (if driver exists)
    - driver_location_lon: Driver's longitude at transition (if driver exists)
    - is_backfilled: Flag for historical data created via backfill command
    """
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='statustransitions'
    )
    from_status = models.IntegerField(
        help_text="Previous order status (1=Pending, 2=Preparing, 3=Ready, 4=Out for Delivery, 5=Delivered, 6=Cancelled, 7=Completed)"
    )
    to_status = models.IntegerField(
        help_text="New order status (1=Pending, 2=Preparing, 3=Ready, 4=Out for Delivery, 5=Delivered, 6=Cancelled, 7=Completed)"
    )
    transitioned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when status transition occurred"
    )
    driver_location_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Driver's latitude at time of transition"
    )
    driver_location_lon = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Driver's longitude at time of transition"
    )
    is_backfilled = models.BooleanField(
        default=False,
        help_text="True if this transition was created by backfill command for historical data"
    )
    
    class Meta:
        db_table = 'dashboard_order_status_transition'
        indexes = [
            models.Index(fields=['order', 'to_status'], name='idx_order_to_status'),
            models.Index(fields=['transitioned_at'], name='idx_transitioned_at'),
        ]
        ordering = ['transitioned_at']
        verbose_name = 'Order Status Transition'
        verbose_name_plural = 'Order Status Transitions'
    
    def __str__(self):
        return f"Order {self.order_id}: {self.from_status} → {self.to_status} at {self.transitioned_at}"
    
    @property
    def has_driver_location(self):
        """Check if driver location data is available"""
        return self.driver_location_lat is not None and self.driver_location_lon is not None
