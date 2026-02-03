from notifications.base import BaseNotifier


class DriverNotifier(BaseNotifier):
    TRIGGER_STATUS = {3}

    def notify(self):
        # Skip notifications for POS orders
        if self.order.is_pos():
            return
        
        if self.order.status not in self.TRIGGER_STATUS:
            return
        
        if not self.order.driver:
            return
        
        payload = {
            "type": "delivery.request",
            "order_id": int(self.order.id),
            'pickup': self.order.get_pickup_location(),
            'drop': self.order.get_delivery_location(),
        }

        self.send(f"driver_{self.order.driver.id}", payload)
