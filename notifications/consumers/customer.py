import json
from channels.generic.websocket import AsyncWebsocketConsumer


class CustomerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.customer_id = self.scope['url_route']['kwargs']['customer_id']
        self.group_name = f"customer_{self.customer_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        print(f"Customer WS connected: {self.group_name}")

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
    
    # Handles: type="review.response"
    async def review_response(self, event):
        """Handle review response notifications"""
        await self.send(text_data=json.dumps({
            "type": "review_response",
            "review_id": event.get("review_id"),
            "response_id": event.get("response_id"),
            "restaurant_name": event.get("restaurant_name"),
            "owner_name": event.get("owner_name"),
            "message": event.get("message"),
        }))
