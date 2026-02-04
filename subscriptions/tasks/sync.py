from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger('subscriptions')


@shared_task(bind=True, max_retries=3)
def sync_stripe_status(self, subscription_id=None):
    """
    Sync subscription status with Stripe.
    Can sync a specific subscription or all active subscriptions.
    
    Args:
        subscription_id (int, optional): Specific subscription to sync
        
    Returns:
        dict: Summary of sync operations
    """
    from subscriptions.models import UserSubscription
    from payment.subscription import SubscriptionService
    
    try:
        # Get subscriptions to sync
        if subscription_id:
            subscriptions = UserSubscription.objects.filter(id=subscription_id)
        else:
            # Sync all active subscriptions with Stripe IDs
            subscriptions = UserSubscription.objects.filter(
                stripe_subscription_id__isnull=False,
                is_active=True
            ).exclude(status=UserSubscription.STATUS_EXPIRED)
        
        synced_count = 0
        updated_count = 0
        
        for subscription in subscriptions:
            try:
                # Retrieve from Stripe
                stripe_sub = SubscriptionService.retrieve_subscription(
                    subscription.stripe_subscription_id
                )
                
                # Update local subscription
                updated = False
                
                # Map Stripe status to our status
                stripe_status = stripe_sub['status']
                if stripe_status == 'active':
                    if subscription.status != UserSubscription.STATUS_ACTIVE:
                        subscription.status = UserSubscription.STATUS_ACTIVE
                        updated = True
                elif stripe_status == 'past_due':
                    if subscription.status != UserSubscription.STATUS_PAST_DUE:
                        subscription.status = UserSubscription.STATUS_PAST_DUE
                        subscription.apply_grace_period()
                        updated = True
                elif stripe_status == 'canceled':
                    if subscription.status != UserSubscription.STATUS_CANCELLED:
                        subscription.status = UserSubscription.STATUS_CANCELLED
                        subscription.auto_renew = False
                        updated = True
                
                # Update period dates
                if stripe_sub.get('current_period_end'):
                    period_end = timezone.datetime.fromtimestamp(
                        stripe_sub['current_period_end'],
                        tz=timezone.get_current_timezone()
                    )
                    if subscription.current_period_end != period_end:
                        subscription.current_period_end = period_end
                        updated = True
                
                if stripe_sub.get('current_period_start'):
                    period_start = timezone.datetime.fromtimestamp(
                        stripe_sub['current_period_start'],
                        tz=timezone.get_current_timezone()
                    )
                    if subscription.current_period_start != period_start:
                        subscription.current_period_start = period_start
                        updated = True
                
                if updated:
                    subscription.save()
                    updated_count += 1
                    logger.info(f"Updated subscription {subscription.id} from Stripe")
                
                synced_count += 1
                
            except Exception as e:
                logger.error(
                    f"Error syncing subscription {subscription.id} with Stripe: {str(e)}"
                )
                continue
        
        logger.info(f"Synced {synced_count} subscription(s), updated {updated_count}")
        return {
            'status': 'success',
            'synced_count': synced_count,
            'updated_count': updated_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in sync_stripe_status: {str(e)}")
        raise self.retry(exc=e, countdown=300)


@shared_task(bind=True, max_retries=3)
def handle_failed_payment(self, subscription_id):
    """
    Handle failed payment by applying grace period.
    Called from webhook processing.
    
    Args:
        subscription_id (int): UserSubscription ID
        
    Returns:
        dict: Result of operation
    """
    from subscriptions.models import UserSubscription
    
    try:
        subscription = UserSubscription.objects.get(id=subscription_id)
        
        # Apply grace period
        subscription.apply_grace_period()
        
        logger.info(f"Applied grace period to subscription {subscription_id}")
        
        # Dispatch payment failed notification
        try:
            from notifications.dispatchers.subscription import SubscriptionNotificationDispatcher
            SubscriptionNotificationDispatcher.dispatch_payment_failed(subscription)
        except ImportError:
            logger.warning("Notification dispatcher not available")
        
        return {
            'status': 'success',
            'subscription_id': subscription_id,
            'grace_period_end': subscription.grace_period_end.isoformat() if subscription.grace_period_end else None
        }
        
    except UserSubscription.DoesNotExist:
        logger.error(f"Subscription {subscription_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error handling failed payment for subscription {subscription_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)
