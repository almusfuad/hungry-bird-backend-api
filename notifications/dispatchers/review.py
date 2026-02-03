from notifications.notifiers import ReviewNotifier, ReviewResponseNotifier
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
