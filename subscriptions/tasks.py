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
                    from subscriptions.dispatchers import SubscriptionNotificationDispatcher
                    dispatcher = SubscriptionNotificationDispatcher()
                    dispatcher.dispatch_subscription_expired(subscription)
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
                from subscriptions.dispatchers import SubscriptionNotificationDispatcher
                dispatcher = SubscriptionNotificationDispatcher()
                dispatcher.dispatch_renewal_reminder(subscription)
                
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
            from subscriptions.dispatchers import SubscriptionNotificationDispatcher
            dispatcher = SubscriptionNotificationDispatcher()
            dispatcher.dispatch_payment_failed(subscription)
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
