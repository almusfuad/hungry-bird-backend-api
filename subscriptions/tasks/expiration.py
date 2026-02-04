from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
import logging

logger = logging.getLogger('subscriptions')


@shared_task(bind=True, max_retries=3)
def check_expired_subscriptions(self):
    """
    Check and expire subscriptions that have passed their grace period.
    Runs daily to downgrade expired subscriptions to Free plan.
    
    Returns:
        dict: Summary of processed subscriptions
    """
    from subscriptions.models import UserSubscription, SubscriptionPlan
    
    try:
        # Get Free plan for downgrading
        free_plan = SubscriptionPlan.objects.get(name='Free')
        
        # Find subscriptions in past_due status with expired grace period
        expired_subscriptions = UserSubscription.objects.filter(
            status=UserSubscription.STATUS_PAST_DUE,
            grace_period_end__lt=timezone.now(),
            is_active=True
        ).exclude(plan__name='Free')
        
        expired_count = 0
        for subscription in expired_subscriptions:
            with transaction.atomic():
                # Mark as expired
                subscription.status = UserSubscription.STATUS_EXPIRED
                subscription.is_active = False
                
                # Downgrade to Free plan
                old_plan = subscription.plan.name
                subscription.plan = free_plan
                subscription.stripe_subscription_id = None
                subscription.current_period_end = None
                subscription.grace_period_end = None
                subscription.save()
                
                # Delete user feature overrides
                subscription.usersubscriptionfeature_set.all().delete()
                
                expired_count += 1
                logger.info(
                    f"Expired subscription {subscription.id} for user {subscription.user.id}, "
                    f"downgraded from {old_plan} to Free"
                )
                
                # Dispatch notification
                try:
                    from notifications.dispatchers.subscription import SubscriptionNotificationDispatcher
                    SubscriptionNotificationDispatcher.dispatch_subscription_expired(subscription)
                except ImportError:
                    logger.warning("Notification dispatcher not available")
        
        logger.info(f"Expired {expired_count} subscription(s)")
        return {
            'status': 'success',
            'expired_count': expired_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except SubscriptionPlan.DoesNotExist:
        logger.error("Free plan does not exist. Cannot process expired subscriptions.")
        raise
    except Exception as e:
        logger.error(f"Error checking expired subscriptions: {str(e)}")
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes
