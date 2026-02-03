from notifications.base import BaseNotifier
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class RestaurantNotifier(BaseNotifier):
    TRIGGER_STATUS = {1, 5, 6}

    def notify(self):
        # Skip notifications for POS orders
        if self.order.is_pos():
            return
        
        if self.order.status not in self.TRIGGER_STATUS:
            return
        
        if not self.order.restaurant:
            return
        
        payload = {
            "type": "order.update",
            "order_id": int(self.order.id),
            "status": self.order.status,
            "message": self.order.get_status_message()
        }

        self.send(f"restaurant_{self.order.restaurant.id}", payload)


class ReviewResponseNotifier:
    """
    Notifier for customers when owner responds to their review.
    """
    def __init__(self, response):
        self.response = response
        self.channel_layer = get_channel_layer()
    
    def notify(self):
        # Check if customer wants notifications
        if not self.response.review.customer:
            return
        
        if not self.response.review.customer.enable_review_notifications:
            return
        
        payload = {
            "type": "review.response",
            "review_id": int(self.response.review.id),
            "response_id": int(self.response.id),
            "restaurant_name": self.response.review.restaurant.name,
            "owner_name": self.response.get_display_name(),
            "message": f"{self.response.review.restaurant.name} responded to your review"
        }
        
        if self.channel_layer:
            async_to_sync(self.channel_layer.group_send)(
                f"customer_{self.response.review.customer.id}",
                payload
            )
