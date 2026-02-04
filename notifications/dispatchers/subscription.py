from django.db import transaction
import logging

logger = logging.getLogger('subscriptions')


class SubscriptionNotificationDispatcher:
    """
    Dispatcher for subscription-related notifications.
    Ensures notifications are sent after database commits.
    """
    
    @classmethod
    def dispatch_subscription_created(cls, subscription):
        """
        Dispatch notification when a new subscription is created.
        
        Args:
            subscription: UserSubscription instance
        """
        def send_notification():
            try:
                from notifications.notifiers.subscription import SubscriptionNotifier
                notifier = SubscriptionNotifier()
                notifier.notify_subscription_change(
                    user_id=subscription.user.id,
                    message=f'Your {subscription.plan.name} subscription has been activated!',
                    subscription_data={
                        'plan_name': subscription.plan.name,
                        'status': subscription.get_status_display(),
                        'event': 'created'
                    }
                )
                logger.info(f"Dispatched subscription created notification for user {subscription.user.id}")
            except Exception as e:
                logger.error(f"Error dispatching subscription created notification: {str(e)}")
        
        transaction.on_commit(send_notification)
    
    @classmethod
    def dispatch_subscription_expired(cls, subscription):
        """
        Dispatch notification when subscription expires.
        
        Args:
            subscription: UserSubscription instance
        """
        def send_notification():
            try:
                from notifications.notifiers.subscription import SubscriptionNotifier
                notifier = SubscriptionNotifier()
                notifier.notify_subscription_change(
                    user_id=subscription.user.id,
                    message='Your subscription has expired and been downgraded to Free plan.',
                    subscription_data={
                        'plan_name': subscription.plan.name,
                        'status': subscription.get_status_display(),
                        'event': 'expired'
                    }
                )
                logger.info(f"Dispatched subscription expired notification for user {subscription.user.id}")
            except Exception as e:
                logger.error(f"Error dispatching subscription expired notification: {str(e)}")
        
        transaction.on_commit(send_notification)
    
    @classmethod
    def dispatch_payment_failed(cls, subscription):
        """
        Dispatch notification when payment fails.
        
        Args:
            subscription: UserSubscription instance
        """
        def send_notification():
            try:
                from notifications.notifiers.subscription import SubscriptionNotifier
                notifier = SubscriptionNotifier()
                
                grace_days = subscription.plan.grace_period_days
                notifier.notify_subscription_change(
                    user_id=subscription.user.id,
                    message=f'Payment failed for your subscription. You have {grace_days} days grace period to update payment method.',
                    subscription_data={
                        'plan_name': subscription.plan.name,
                        'status': subscription.get_status_display(),
                        'grace_period_end': subscription.grace_period_end.isoformat() if subscription.grace_period_end else None,
                        'event': 'payment_failed'
                    }
                )
                logger.info(f"Dispatched payment failed notification for user {subscription.user.id}")
            except Exception as e:
                logger.error(f"Error dispatching payment failed notification: {str(e)}")
        
        transaction.on_commit(send_notification)
    
    @classmethod
    def dispatch_renewal_reminder(cls, subscription):
        """
        Dispatch reminder notification before subscription renewal.
        
        Args:
            subscription: UserSubscription instance
        """
        def send_notification():
            try:
                from notifications.notifiers.subscription import SubscriptionNotifier
                notifier = SubscriptionNotifier()
                
                days_remaining = subscription.days_remaining()
                notifier.notify_subscription_change(
                    user_id=subscription.user.id,
                    message=f'Your {subscription.plan.name} subscription will renew in {days_remaining} days.',
                    subscription_data={
                        'plan_name': subscription.plan.name,
                        'status': subscription.get_status_display(),
                        'days_remaining': days_remaining,
                        'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                        'event': 'renewal_reminder'
                    }
                )
                logger.info(f"Dispatched renewal reminder notification for user {subscription.user.id}")
            except Exception as e:
                logger.error(f"Error dispatching renewal reminder notification: {str(e)}")
        
        transaction.on_commit(send_notification)
    
    @classmethod
    def dispatch_subscription_upgraded(cls, subscription, old_plan_name):
        """
        Dispatch notification when subscription is upgraded.
        
        Args:
            subscription: UserSubscription instance
            old_plan_name: Name of previous plan
        """
        def send_notification():
            try:
                from notifications.notifiers.subscription import SubscriptionNotifier
                notifier = SubscriptionNotifier()
                notifier.notify_subscription_change(
                    user_id=subscription.user.id,
                    message=f'Your subscription has been upgraded from {old_plan_name} to {subscription.plan.name}!',
                    subscription_data={
                        'plan_name': subscription.plan.name,
                        'old_plan_name': old_plan_name,
                        'status': subscription.get_status_display(),
                        'event': 'upgraded'
                    }
                )
                logger.info(f"Dispatched subscription upgraded notification for user {subscription.user.id}")
            except Exception as e:
                logger.error(f"Error dispatching subscription upgraded notification: {str(e)}")
        
        transaction.on_commit(send_notification)
    
    @classmethod
    def dispatch_subscription_cancelled(cls, subscription):
        """
        Dispatch notification when subscription is cancelled.
        
        Args:
            subscription: UserSubscription instance
        """
        def send_notification():
            try:
                from notifications.notifiers.subscription import SubscriptionNotifier
                notifier = SubscriptionNotifier()
                
                message = f'Your {subscription.plan.name} subscription has been cancelled.'
                if subscription.current_period_end:
                    message += f' You will retain access until {subscription.current_period_end.strftime("%B %d, %Y")}.'
                
                notifier.notify_subscription_change(
                    user_id=subscription.user.id,
                    message=message,
                    subscription_data={
                        'plan_name': subscription.plan.name,
                        'status': subscription.get_status_display(),
                        'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                        'event': 'cancelled'
                    }
                )
                logger.info(f"Dispatched subscription cancelled notification for user {subscription.user.id}")
            except Exception as e:
                logger.error(f"Error dispatching subscription cancelled notification: {str(e)}")
        
        transaction.on_commit(send_notification)
