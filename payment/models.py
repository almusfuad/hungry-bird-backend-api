from django.db import models
from hungryBird.baseModels import TimeStampedModel, LocationModel


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
    


