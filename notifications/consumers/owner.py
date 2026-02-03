import json
from channels.generic.websocket import AsyncWebsocketConsumer


class RestaurantOwnerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.restaurant_id = self.scope['url_route']['kwargs']['restaurant_id']
        self.group_name = f"restaurant_{self.restaurant_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        print(f"Restaurant WS connected: {self.group_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Handles: type="order.update"
    async def order_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "order_update",
            "order_id": event.get("order_id"),
            "status": event.get("status"),
            "message": event.get("message"),
        }))
    
    # Handles: type="review.new"
    async def review_new(self, event):
        """Handle new review notifications"""
        await self.send(text_data=json.dumps({
            "type": "review_new",
            "review_id": event.get("review_id"),
            "restaurant_id": event.get("restaurant_id"),
            "menu_item_id": event.get("menu_item_id"),
            "rating": event.get("rating"),
            "customer_name": event.get("customer_name"),
            "message": event.get("message"),
        }))
