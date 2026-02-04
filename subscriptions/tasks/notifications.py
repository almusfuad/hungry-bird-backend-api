from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('subscriptions')


@shared_task(bind=True, max_retries=3)
def send_renewal_reminders(self):
    """
    Send renewal reminders to users whose subscriptions are expiring soon.
    Runs daily to notify users 3 days before expiration.
    
    Returns:
        dict: Summary of reminders sent
    """
    from subscriptions.models import UserSubscription
    
    try:
        # Find subscriptions expiring in 3 days
        three_days_from_now = timezone.now() + timedelta(days=3)
        
        expiring_subscriptions = UserSubscription.objects.filter(
            status=UserSubscription.STATUS_ACTIVE,
            current_period_end__date=three_days_from_now.date(),
            auto_renew=True,
            is_active=True
        ).exclude(plan__name='Free')
        
        reminder_count = 0
        for subscription in expiring_subscriptions:
            try:
                # Dispatch renewal reminder notification
                from notifications.dispatchers.subscription import SubscriptionNotificationDispatcher
                SubscriptionNotificationDispatcher.dispatch_renewal_reminder(subscription)
                
                reminder_count += 1
                logger.info(f"Sent renewal reminder for subscription {subscription.id}")
            except ImportError:
                logger.warning("Notification dispatcher not available")
                break
        
        logger.info(f"Sent {reminder_count} renewal reminder(s)")
        return {
            'status': 'success',
            'reminder_count': reminder_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending renewal reminders: {str(e)}")
        raise self.retry(exc=e, countdown=300)
