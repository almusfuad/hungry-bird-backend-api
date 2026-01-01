from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
import stripe
from hungryBird.permissions import IsCustomer
from order.models import Order


# Create your views here.
class CompletePaymentView(APIView):
    permission_classes = [IsCustomer]

    def patch(self, request, order_id):
        try:
            order = Order.objects.select_related(
                'payment'
            ).get(id=order_id, customer=request.user)
            payment = order.payment
            if payment.method == 1:
                return Response({'detail': "Cash on Delivery does not require online payment."}, status=400)
            elif payment.method == 2:
                token = request.data.get('token')
                charge = stripe.Charge.create(
                    amount=int(payment.amount * 100),
                    currency='usd',
                    description=f'Order #{order.id}',
                    source=token,
                )
                payment.stripe_charge_id = charge.id
                payment.status = 1  # Completed
                payment.save()
            return Response({'detail': "Payment completed successfully."})
        except Order.DoesNotExist:
            return Response({'detail': "Order not found."}, status=404)
        except stripe.error.StripeError as e:
            return Response({'detail': str(e)}, status=400)
