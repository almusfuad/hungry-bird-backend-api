from notifications.base import BaseNotifier



class DriverNotifier(BaseNotifier):
    TRIGGER_STATUS = {3}


    def notify(self):
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




class RestaurantNotifier(BaseNotifier):
    TRIGGER_STATUS = {1, 5, 6}

    def notify(self):
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




class CustomerNotifier(BaseNotifier):
    TRIGGER_STATUS = {2, 4}


    def notify(self):
        if self.order.status not in self.TRIGGER_STATUS:
            return
        
        payload = {
            "type": "order.update",
            "order_id": int(self.order.id),
            "status": self.order.status,
            "message": self.order.get_status_message()
        }


        self.send(f"customer_{self.order.customer.id}", payload)

