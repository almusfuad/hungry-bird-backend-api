from notifications.notifiers import ReviewNotifier, ReviewResponseNotifier
from notifications.notifiers.customer import ReviewPromptNotifier
import logging

logger = logging.getLogger(__name__)


class ReviewNotificationDispatcher:
    """
    Dispatcher for review-related notifications.
    """
    
    @classmethod
    def dispatch_new_review(cls, review):
        """Dispatch notification when a new review is created."""
        try:
            notifier = ReviewNotifier(review)
            notifier.notify()
        except Exception as e:
            logger.exception(
                "Failed to send new review notification for review %s",
                review.id
            )
    
    @classmethod
    def dispatch_review_response(cls, response):
        """Dispatch notification when owner responds to a review."""
        try:
            notifier = ReviewResponseNotifier(response)
            notifier.notify()
        except Exception as e:
            logger.exception(
                "Failed to send review response notification for response %s",
                response.id
            )
    
    @classmethod
    def dispatch_review_prompt(cls, order):
        """
        Dispatch review prompt notification to customer after order delivery.
        
        This method is called by a Celery task 1 hour after order delivery
        to encourage the customer to leave a review.
        
        Args:
            order: Order instance that was delivered
        """
        try:
            notifier = ReviewPromptNotifier(order)
            notifier.notify()
        except Exception as e:
            logger.exception(
                "Failed to send review prompt notification for order %s",
                order.id
            )
