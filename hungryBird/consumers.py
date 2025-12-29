import json
from channels.generic.websocket import AsyncWebsocketConsumer


class DriverConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.driver_id = self.scope['url_route']['kwargs']['driver_id']
        self.group_name = f"driver_{self.driver_id}"

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


    