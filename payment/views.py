from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
import stripe
from hungryBird.permissions import IsCustomer
from order.models import Order
from payment.models import Payment
from hungryBird.settings import STRIPE_SECRET_KEY

stripe.api_key = STRIPE_SECRET_KEY




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
