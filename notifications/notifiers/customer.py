from notifications.base import BaseNotifier


class CustomerNotifier(BaseNotifier):
    TRIGGER_STATUS = {2, 4}

    def notify(self):
        # Skip notifications for POS orders
        if self.order.is_pos():
            return
        
        if self.order.status not in self.TRIGGER_STATUS:
            return
        
        payload = {
            "type": "order.update",
            "order_id": int(self.order.id),
            "status": self.order.status,
            "message": self.order.get_status_message()
        }

        self.send(f"customer_{self.order.customer.id}", payload)


class ReviewPromptNotifier(BaseNotifier):
    """
    Sends a review prompt notification to customer after order delivery.
    
    This notifier is triggered by a Celery task 1 hour after order is delivered,
    prompting the customer to leave a review for their completed order.
    """
    
    def notify(self):
        # Skip notifications for POS orders
        if self.order.is_pos():
            return
        
        # Only send for delivered orders
        if self.order.status != 5:
            return
        
        # Check if customer wants review notifications
        if not hasattr(self.order.customer, 'enable_review_notifications') or \
           not self.order.customer.enable_review_notifications:
            return
        
        payload = {
            "type": "review.prompt",
            "order_id": int(self.order.id),
            "restaurant_id": int(self.order.restaurant.id),
            "restaurant_name": self.order.restaurant.name,
            "message": f"How was your order from {self.order.restaurant.name}? Leave a review!"
        }
        
        self.send(f"customer_{self.order.customer.id}", payload)
