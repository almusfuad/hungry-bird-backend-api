from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger('review')


@shared_task(bind=True, max_retries=3)
def send_review_prompt(self, order_id):
    """
    Send a review prompt to customer 1 hour after order delivery.
    
    This task is scheduled when an order status changes to Delivered (status=5).
    It sends a WebSocket notification to the customer encouraging them to leave a review.
    
    Args:
        order_id (int): The ID of the delivered order
        
    Returns:
        dict: Summary of the review prompt sent
    """
    from order.models import Order
    from notifications.dispatchers.review import ReviewNotificationDispatcher
    
    try:
        # Fetch the order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} not found for review prompt")
            return {
                'status': 'error',
                'message': f'Order {order_id} not found',
                'timestamp': timezone.now().isoformat()
            }
        
        # Verify order is still in delivered status
        if order.status != 5:
            logger.info(f"Order {order_id} status changed from delivered. Current status: {order.status}")
            return {
                'status': 'skipped',
                'message': f'Order status is no longer delivered (current: {order.status})',
                'timestamp': timezone.now().isoformat()
            }
        
        # Check if customer has already reviewed this order
        from review.models import Review
        existing_review = Review.objects.filter(
            order=order,
            customer=order.customer,
            is_active=True
        ).exists()
        
        if existing_review:
            logger.info(f"Customer {order.customer.id} already reviewed order {order_id}")
            return {
                'status': 'skipped',
                'message': 'Customer already reviewed this order',
                'timestamp': timezone.now().isoformat()
            }
        
        # Dispatch review prompt notification
        ReviewNotificationDispatcher.dispatch_review_prompt(order)
        
        logger.info(f"Sent review prompt for order {order_id} to customer {order.customer.id}")
        return {
            'status': 'success',
            'order_id': order_id,
            'customer_id': order.customer.id,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending review prompt for order {order_id}: {str(e)}")
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes
