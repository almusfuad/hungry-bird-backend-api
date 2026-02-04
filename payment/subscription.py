import stripe
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('payment')

# Initialize Stripe with secret key
stripe.api_key = settings.STRIPE_SECRET_KEY


class SubscriptionService:
    """
    Service class for managing Stripe subscription operations.
    Handles customer creation, subscription management, and webhook processing.
    """

    @staticmethod
    def create_stripe_customer(user):
        """
        Create a Stripe customer for the given user.
        
        Args:
            user: User instance (restaurant owner)
            
        Returns:
            str: Stripe customer ID
            
        Raises:
            stripe.error.StripeError: If customer creation fails
        """
        try:
            customer = stripe.Customer.create(
                email=user.email if hasattr(user, 'email') and user.email else None,
                phone=user.phone if hasattr(user, 'phone') else None,
                name=user.username,
                metadata={
                    'user_id': user.id,
                    'role': user.role,
                    'username': user.username
                }
            )
            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer for user {user.id}: {str(e)}")
            raise

    @staticmethod
    def create_subscription(customer_id, price_id, payment_method_id=None, trial_period_days=None):
        """
        Create a Stripe subscription for a customer.
        
        Args:
            customer_id (str): Stripe customer ID
            price_id (str): Stripe price ID for the subscription plan
            payment_method_id (str, optional): Stripe payment method ID
            trial_period_days (int, optional): Number of days for trial period
            
        Returns:
            dict: Stripe subscription object
            
        Raises:
            stripe.error.StripeError: If subscription creation fails
        """
        try:
            subscription_params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'expand': ['latest_invoice.payment_intent'],
            }
            
            if payment_method_id:
                subscription_params['default_payment_method'] = payment_method_id
            
            if trial_period_days:
                subscription_params['trial_period_days'] = trial_period_days
            
            # Enable automatic payment collection
            subscription_params['payment_behavior'] = 'default_incomplete'
            subscription_params['payment_settings'] = {
                'payment_method_types': ['card'],
                'save_default_payment_method': 'on_subscription'
            }
            
            subscription = stripe.Subscription.create(**subscription_params)
            
            logger.info(f"Created subscription {subscription.id} for customer {customer_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription for customer {customer_id}: {str(e)}")
            raise

    @staticmethod
    def cancel_subscription(subscription_id, at_period_end=True):
        """
        Cancel a Stripe subscription.
        
        Args:
            subscription_id (str): Stripe subscription ID
            at_period_end (bool): If True, cancel at period end; if False, cancel immediately
            
        Returns:
            dict: Updated Stripe subscription object
            
        Raises:
            stripe.error.StripeError: If cancellation fails
        """
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
                logger.info(f"Scheduled cancellation for subscription {subscription_id} at period end")
            else:
                subscription = stripe.Subscription.delete(subscription_id)
                logger.info(f"Immediately cancelled subscription {subscription_id}")
            
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {str(e)}")
            raise

    @staticmethod
    def update_subscription(subscription_id, new_price_id, proration_behavior='create_prorations'):
        """
        Update a subscription to a new price/plan.
        
        Args:
            subscription_id (str): Stripe subscription ID
            new_price_id (str): New Stripe price ID
            proration_behavior (str): How to handle proration ('create_prorations', 'none', 'always_invoice')
            
        Returns:
            dict: Updated Stripe subscription object
            
        Raises:
            stripe.error.StripeError: If update fails
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            subscription = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id,
                }],
                proration_behavior=proration_behavior
            )
            
            logger.info(f"Updated subscription {subscription_id} to new price {new_price_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription {subscription_id}: {str(e)}")
            raise

    @staticmethod
    def retrieve_subscription(subscription_id):
        """
        Retrieve a subscription from Stripe.
        
        Args:
            subscription_id (str): Stripe subscription ID
            
        Returns:
            dict: Stripe subscription object
            
        Raises:
            stripe.error.StripeError: If retrieval fails
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve subscription {subscription_id}: {str(e)}")
            raise

    @staticmethod
    def handle_webhook_event(event):
        """
        Process Stripe webhook events for subscriptions.
        
        Args:
            event (dict): Stripe event object
            
        Returns:
            dict: Processing result with status and message
        """
        event_type = event['type']
        data_object = event['data']['object']
        
        logger.info(f"Processing webhook event: {event_type}")
        
        try:
            if event_type == 'customer.subscription.created':
                return SubscriptionService._handle_subscription_created(data_object)
            
            elif event_type == 'customer.subscription.updated':
                return SubscriptionService._handle_subscription_updated(data_object)
            
            elif event_type == 'customer.subscription.deleted':
                return SubscriptionService._handle_subscription_deleted(data_object)
            
            elif event_type == 'customer.subscription.trial_will_end':
                return SubscriptionService._handle_trial_ending(data_object)
            
            elif event_type == 'invoice.payment_failed':
                return SubscriptionService._handle_payment_failed(data_object)
            
            elif event_type == 'invoice.payment_succeeded':
                return SubscriptionService._handle_payment_succeeded(data_object)
            
            else:
                logger.info(f"Unhandled event type: {event_type}")
                return {'status': 'ignored', 'message': f'Event type {event_type} not handled'}
                
        except Exception as e:
            logger.error(f"Error processing webhook event {event_type}: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @staticmethod
    def _handle_subscription_created(subscription):
        """Handle subscription.created event"""
        logger.info(f"Subscription created: {subscription['id']}")
        return {
            'status': 'success',
            'message': 'Subscription created',
            'subscription_id': subscription['id'],
            'customer_id': subscription['customer'],
            'status_value': subscription['status']
        }

    @staticmethod
    def _handle_subscription_updated(subscription):
        """Handle subscription.updated event"""
        logger.info(f"Subscription updated: {subscription['id']}, status: {subscription['status']}")
        return {
            'status': 'success',
            'message': 'Subscription updated',
            'subscription_id': subscription['id'],
            'subscription_status': subscription['status'],
            'current_period_end': subscription['current_period_end'],
            'cancel_at_period_end': subscription.get('cancel_at_period_end', False)
        }

    @staticmethod
    def _handle_subscription_deleted(subscription):
        """Handle subscription.deleted event"""
        logger.info(f"Subscription deleted: {subscription['id']}")
        return {
            'status': 'success',
            'message': 'Subscription deleted',
            'subscription_id': subscription['id']
        }

    @staticmethod
    def _handle_trial_ending(subscription):
        """Handle subscription.trial_will_end event"""
        logger.info(f"Trial ending for subscription: {subscription['id']}")
        return {
            'status': 'success',
            'message': 'Trial ending soon',
            'subscription_id': subscription['id'],
            'trial_end': subscription.get('trial_end')
        }

    @staticmethod
    def _handle_payment_failed(invoice):
        """Handle invoice.payment_failed event"""
        subscription_id = invoice.get('subscription')
        logger.warning(f"Payment failed for subscription: {subscription_id}")
        return {
            'status': 'success',
            'message': 'Payment failed',
            'subscription_id': subscription_id,
            'invoice_id': invoice['id'],
            'amount_due': invoice.get('amount_due')
        }

    @staticmethod
    def _handle_payment_succeeded(invoice):
        """Handle invoice.payment_succeeded event"""
        subscription_id = invoice.get('subscription')
        logger.info(f"Payment succeeded for subscription: {subscription_id}")
        return {
            'status': 'success',
            'message': 'Payment succeeded',
            'subscription_id': subscription_id,
            'invoice_id': invoice['id'],
            'amount_paid': invoice.get('amount_paid')
        }

    @staticmethod
    def verify_webhook_signature(payload, sig_header, webhook_secret):
        """
        Verify Stripe webhook signature.
        
        Args:
            payload (bytes): Raw request body
            sig_header (str): Stripe-Signature header value
            webhook_secret (str): Stripe webhook secret
            
        Returns:
            dict: Constructed event object if valid
            
        Raises:
            stripe.error.SignatureVerificationError: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            logger.info(f"Webhook signature verified for event: {event['type']}")
            return event
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            raise
