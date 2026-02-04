from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger('subscriptions')


class SubscriptionNotifier:
    """
    Notifier for sending subscription-related notifications via WebSocket.
    Uses Django Channels for real-time notifications.
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def notify_subscription_change(self, user_id, message, subscription_data):
        """
        Send subscription change notification to restaurant owner.
        
        Args:
            user_id (int): Restaurant owner user ID
            message (str): Notification message
            subscription_data (dict): Subscription details
        """
        try:
            # Channel group name for restaurant owner
            group_name = f'restaurant_{user_id}'
            
            # Notification payload
            notification = {
                'type': 'subscription_notification',
                'message': message,
                'data': subscription_data,
                'timestamp': subscription_data.get('timestamp', None)
            }
            
            # Send to channel group
            async_to_sync(self.channel_layer.group_send)(
                group_name,
                {
                    'type': 'send_notification',
                    'notification': notification
                }
            )
            
            logger.info(f"Sent subscription notification to group {group_name}: {message}")
            
        except Exception as e:
            logger.error(f"Error sending subscription notification to user {user_id}: {str(e)}")
            raise
