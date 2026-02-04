from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
import stripe
from hungryBird.permissions import IsCustomer
from order.models import Order
from payment.models import Payment
from hungryBird.settings import STRIPE_SECRET_KEY
import logging
import os

stripe.api_key = STRIPE_SECRET_KEY
logger = logging.getLogger('payment')




# Create your views here.
class StripeWebhookView(APIView):
    permission_classes = [IsCustomer]

    def post(self, request):
        # Parse the event from Stripe
        event = stripe.Event.construct_from(
            request.data, stripe.api_key
        )

        # Handle the event
        if event.type == 'charge.succeeded':
            charge = event.data.object
            payment = Payment.objects.get(transaction_id=charge.id)
            payment.status = 1  # Completed
            payment.save(update_fields=['status', 'updated_at'])


        return Response(status=200)


@csrf_exempt
@api_view(['POST'])
def subscription_webhook_handler(request):
    """
    Webhook handler for Stripe subscription events.
    Handles subscription lifecycle events and updates local database.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return Response({'error': 'Webhook secret not configured'}, status=500)
    
    try:
        # Verify webhook signature
        from payment.subscription import SubscriptionService
        event = SubscriptionService.verify_webhook_signature(
            payload, sig_header, webhook_secret
        )
        
        # Process the event
        result = SubscriptionService.handle_webhook_event(event)
        
        # Handle specific subscription events that need database updates
        event_type = event['type']
        
        if event_type in ['customer.subscription.updated', 'customer.subscription.deleted', 
                          'invoice.payment_failed', 'invoice.payment_succeeded']:
            # Import here to avoid circular imports
            from subscriptions.models import UserSubscription
            from subscriptions.tasks import sync_stripe_status, handle_failed_payment
            from django.utils import timezone
            
            data_object = event['data']['object']
            
            # Get subscription ID from event
            if event_type.startswith('customer.subscription'):
                stripe_subscription_id = data_object['id']
            elif event_type.startswith('invoice'):
                stripe_subscription_id = data_object.get('subscription')
            else:
                stripe_subscription_id = None
            
            if stripe_subscription_id:
                try:
                    # Find local subscription
                    subscription = UserSubscription.objects.get(
                        stripe_subscription_id=stripe_subscription_id
                    )
                    
                    # Handle payment failure specifically
                    if event_type == 'invoice.payment_failed':
                        handle_failed_payment.delay(subscription.id)
                    else:
                        # Sync other events
                        sync_stripe_status.delay(subscription.id)
                    
                except UserSubscription.DoesNotExist:
                    logger.warning(
                        f"Received webhook for unknown subscription: {stripe_subscription_id}"
                    )
        
        logger.info(f"Processed webhook event: {event_type}")
        return Response({'status': 'success', 'result': result}, status=200)
        
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        return Response({'error': 'Invalid signature'}, status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return Response({'error': str(e)}, status=500)
