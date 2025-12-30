from django.db import models, transaction
from hungryBird.baseModels import TimeStampedModel, LocationModel
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework.exceptions import PermissionDenied
import json
from notifications.dispatcher import OrderNotificationDispatcher

# Create your models here.
class Order(TimeStampedModel, LocationModel):
    STATUS_CHOICES = [
        (1, 'Pending'),
        (2, 'Preparing'),
        (3, 'Ready for Pickup'),
        (4, 'Out for Delivery'),
        (5, 'Delivered'),
        (6, 'Cancelled'),
    ]

    STATUS_MESSAGES = {
        1: "A new order is placed. Check details.",
        2: "Chef is preparing your order. Hold tight!",
        3: "An order is ready to delivered. Please pick it up.",
        4: "Your order is on the way! Get ready to receive it.",
        5: "Order delivered successfully. Thanks Chef!",
        6: "Order is cancelled."
    }


    customer = models.ForeignKey(
        'authUser.User', on_delete=models.DO_NOTHING, related_name='orders',
        limit_choices_to={'role': 1}
    )
    restaurant = models.ForeignKey(
        'restaurant.Restaurant', on_delete=models.DO_NOTHING, related_name='orders'
    )
    driver = models.ForeignKey(
        'authUser.User', on_delete=models.DO_NOTHING, related_name='deliveries',
        limit_choices_to={'role': 3},
        null=True, blank=True
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_address = models.TextField()

    # Helpers
    def get_status_message(self):
        return self.STATUS_MESSAGES.get(
            self.status, "Order status has been updated."
        )


    # Domain Logic Methods
    def can_edit(self):
        return self.status in [1, 2] \
             or self.created_at >= \
                 timezone.now() - timezone.timedelta(minutes=5) # Pending or Preparing
    
    def get_pickup_location(self):
        return {
            'pick_lat': float(self.restaurant.latitude),
            'pick_lng': float(self.restaurant.longitude)
        }
    
    def get_delivery_location(self):
        return {
            'delivery_lat': float(self.latitude),
            'delivery_lng': float(self.longitude)
        }
    
    def get_order_total(self):
        total = sum([item.get_item_total() for item in self.order_items.all()])
        total += sum([add_on.get_add_on_total() for item in self.order_items.all() \
                      for add_on in item.order_add_ons.all()])
        return total
    

    # State Transitions
    def _allowed_transitions(self):
        return {
            1: {
                1: [6], # Customer can cancel
                2: [6]
            },
            2: {  # Owner can change status from preparing to out for delivery
                1: [2],
                2: [3],
                3: [4],
            },
            3: { # Driver can change status from ready for pickup to delivered
                3: [4],
                4: [5],
            }
        }


    def transition_status(self, user, new_status):
        role = int(user.role)
        current_status = self.status

        allowed = self._allowed_transitions().get(role, {}). \
            get(current_status, [])
        
        if new_status not in allowed:
            raise PermissionDenied("Invalid status transition.")
        
        

        with transaction.atomic():
            self.status = new_status
            self.save(update_fields=['status', 'updated_at'])  
    
            # If order is cancelled, no further actions needed
            if new_status == 6:
                transaction.on_commit(
                    lambda: OrderNotificationDispatcher.dispatch(self)
                )
                return

            if new_status == 3 and not self.driver:  # Ready for Pickup by Owner
                driver = self.restaurant.assign_driver(self)
                if driver:
                    self.driver = driver
                    print(f"Assigned driver {driver.id} to order {self.id}")
                    self.save(update_fields=['driver'])
                    transaction.on_commit(
                        lambda: OrderNotificationDispatcher.dispatch(self)
                    )
                    return

            # Always notify on status change
            transaction.on_commit(
                lambda: OrderNotificationDispatcher.dispatch(self)
            )   


    def __str__(self):
        return f"Order #{self.id} by {self.customer.username}"
    





class OrderItem(TimeStampedModel):
    order = models.ForeignKey('order.Order', on_delete=models.DO_NOTHING, related_name='order_items')
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()


    def get_item_total(self):
        return self.menu_item.price * self.quantity
    

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name} for Order #{self.order.id}"
    

class OrderAddOn(TimeStampedModel):
    order_item = models.ForeignKey('order.OrderItem', 
        on_delete=models.CASCADE, related_name='order_add_ons')
    add_on = models.ForeignKey('restaurant.AddOn', on_delete=models.DO_NOTHING)
    quantity = models.PositiveIntegerField()


    def get_add_on_total(self):
        return self.add_on.price * self.quantity
    
    def __str__(self):
        return f"{self.quantity} x {self.add_on.name} for OrderItem #{self.order_item.id}"
    
