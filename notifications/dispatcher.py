from notifications.notifiers import (
    DriverNotifier,
    RestaurantNotifier,
    CustomerNotifier
)
import logging

logger = logging.getLogger(__name__)


def dispatch_notification(type, recipient, data):
    """
    Generic notification dispatcher for any type of notification.
    
    Args:
        type (str): Type of notification (e.g., 'new_review', 'review_response')
        recipient (User): The user to receive the notification
        data (dict): Notification data including message and related info
    """
    try:
        # Import here to avoid circular imports
        from notifications.base import BaseNotifier
        
        # Create a simple notification using the base notifier
        # In a real-world scenario, you might have specific notifiers for different types
        notifier = BaseNotifier(recipient, data)
        notifier.notify()
        
        logger.info(
            f"Notification dispatched: type={type}, recipient={recipient.username}, data={data}"
        )
    except Exception as e:
        logger.exception(
            f"Failed to dispatch notification: type={type}, recipient={recipient.username}"
        )


class OrderNotificationDispatcher:
    NOTIFIERS = [
        DriverNotifier,
        RestaurantNotifier,
        CustomerNotifier
    ]


    @classmethod
    def dispatch(cls, order):
        for notifier_cls in cls.NOTIFIERS:
            try:
                notifier = notifier_cls(order)
                notifier.notify()
            except Exception as e:
                logger.exception(
                    "Notification failed: %s for order %s",
                    notifier_cls.__name__,
                    order.id,
                )
                continue
