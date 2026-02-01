import json
from channels.generic.websocket import AsyncWebsocketConsumer


class DriverConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.driver_id = self.scope['url_route']['kwargs']['driver_id']
        self.group_name = f"driver_{self.driver_id}"


        print("WebSocket connected to group:", self.group_name)

        # Join driver group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()


    async def disconnect(self, close_code):
        # Leave driver group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )


    # Receive message from group
    async def delivery_request(self, event):
        await self.send(text_data=json.dumps({
            'type': 'delivery_request',
            'order_id': event['order_id'],
            'pickup': event['pickup'],
            'drop': event['drop'],
        }))



class RestaurantConsumer(AsyncWebsocketConsumer):
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

        