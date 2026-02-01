'''
This files handle Channels safety and correctness.
'''


import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync




class BaseNotifier:
    """
    Base class for all notifiers.
    """

    def __init__(self, order):
        self.order = order
        self.channel_layer = get_channel_layer()

    
    def notify(self):
        raise NotImplementedError("Subclasses must implement this method.")
    

    def send(self, group_name, payload):
        if not self.channel_layer:
            print("Channel layer:", self.channel_layer)
            return
        
        async_to_sync(self.channel_layer.group_send)(
            group_name,
            # json.loads(json.dumps(payload))
            payload
        )

