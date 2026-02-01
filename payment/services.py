import stripe

class PaymentService:
    @staticmethod
    def create_stripe_charge(payment, token):
        if payment.method != payment.METHOD_CHOICES[1][0]:  # Stripe method
            raise ValueError("Invalid payment method.")
        
        charge = stripe.Charge.create(
            amount=int(payment.amount * 100),
            currency='usd',
            description=f'Order #{payment.order.id}',
            source=token,
            idempotency_key=f"payment_{payment.id}"
        )

        return charge