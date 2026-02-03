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
