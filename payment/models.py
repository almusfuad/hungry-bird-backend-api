from django.db import models
from hungryBird.baseModels import TimeStampedModel, LocationModel
from django.db.transaction import atomic
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Create your models here.
class Payment(TimeStampedModel):
    METHOD_CHOICES = [
        (1, 'Cash on Delivery'),
        (2, 'Stripe'),
        # (3, 'PayPal'),
        # (4, 'Razorpay'),
        # (5, 'Google Pay'),
        # (6, 'Apple Pay'),
        # (7, 'Bank Transfer'),
        # (8, 'Cryptocurrency'),
        (9, 'Other'),
    ]

    STATUS = [
        (0, 'Pending'),
        (1, 'Completed'),
        (2, 'Failed'),
        (3, 'Refunded'),
    ]
    order = models.OneToOneField('order.Order', on_delete=models.DO_NOTHING, related_name='payment')
    method = models.PositiveSmallIntegerField(choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.PositiveSmallIntegerField(choices=STATUS, default=0)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Payment {self.id} - Order {self.order.id} - {self.get_status_display()}"
    


# Signal for order status changes
@receiver(post_save, sender='order.Order')
def handle_order_status_change(post_save, instance, **kwargs):
    if instance.status == 3 and not instance.driver:
        driver = instance.restaurant.assign_driver(instance)
        if driver:
            # Notify driver via Channels
            channel = get_channel_layer()
            async_to_sync(channel.group_send)(
                f"driver_{driver.id}",
                {
                    'type': 'delivery.request',
                    'order_id': instance.id,
                    'pickup': instance.get_pickup_location(),
                    'drop': instance.get_delivery_location(),
                }
            )