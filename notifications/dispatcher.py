from notifications.notifiers import (
    DriverNotifier,
    RestaurantNotifier,
    CustomerNotifier
)
import logging

logger = logging.getLogger(__name__)



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
