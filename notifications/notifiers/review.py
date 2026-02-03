from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class ReviewNotifier:
    """
    Notifier for restaurant owners when they receive a new review.
    """
    def __init__(self, review):
        self.review = review
        self.channel_layer = get_channel_layer()
    
    def notify(self):
        # Check if owner wants notifications
        if not self.review.restaurant.owner:
            return
        
        if not self.review.restaurant.owner.enable_review_notifications:
            return
        
        payload = {
            "type": "review.new",
            "review_id": int(self.review.id),
            "restaurant_id": int(self.review.restaurant.id),
            "menu_item_id": int(self.review.menu_item.id) if self.review.menu_item else None,
            "rating": float(self.review.rating),
            "customer_name": self.review.get_display_name(),
            "message": f"New review received for {self.review.menu_item.name if self.review.menu_item else self.review.restaurant.name}"
        }
        
        if self.channel_layer:
            async_to_sync(self.channel_layer.group_send)(
                f"restaurant_{self.review.restaurant.owner.id}",
                payload
            )
