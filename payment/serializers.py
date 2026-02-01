from rest_framework import serializers
from .models import Payment
import datetime


class CheckCardInformation:
    def __init__(self):
        pass

    def check_expiry_month(self, value):
        if not (1 <= value <= 12):
            raise serializers.ValidationError("Expiry month must be between 1 and 12.")
        return value
    
    def check_expiry_year(self, value):
        current_year = datetime.datetime.now().year % 100  # Get last two digits of current year
        if value < current_year:
            raise serializers.ValidationError("Expiry year cannot be in the past.")
        return value
    
    def check_cvv(self, value):
        if not (100 <= value <= 9999):
            raise serializers.ValidationError("CVV must be a 3 or 4 digit number.")
        return value
    
    def check_payment_method(self, value):
        if value.lower() not in ['card']:
            raise serializers.ValidationError("Invalid payment method.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'method', 'amount', 'status', 'transaction_id', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']