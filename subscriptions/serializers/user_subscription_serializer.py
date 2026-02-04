from rest_framework import serializers
from django.utils import timezone
from subscriptions.models import UserSubscription, SubscriptionPlan
from subscriptions.serializers.subscription_plan_serializer import SubscriptionPlanSerializer
from subscriptions.serializers.feature_serializer import FeatureSerializer


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for UserSubscription model.
    Shows effective features considering per-user overrides.
    """
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        source='plan',
        write_only=True,
        required=False
    )
    
    # Write-only field for subscription creation
    payment_method_id = serializers.CharField(
        write_only=True,
        required=False,
        help_text="Stripe payment method ID for paid subscriptions"
    )
    
    # Computed fields
    is_expired = serializers.SerializerMethodField()
    in_grace_period = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    effective_features = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'id',
            'user',
            'plan',
            'plan_id',
            'payment_method_id',
            'status',
            'status_display',
            'current_period_start',
            'current_period_end',
            'grace_period_end',
            'auto_renew',
            'is_expired',
            'in_grace_period',
            'days_remaining',
            'effective_features',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'user',
            'status',
            'status_display',
            'current_period_start',
            'current_period_end',
            'grace_period_end',
            'is_expired',
            'in_grace_period',
            'days_remaining',
            'effective_features',
            'created_at',
            'updated_at'
        ]
    
    def get_is_expired(self, obj):
        """Check if subscription is expired"""
        return obj.is_expired()
    
    def get_in_grace_period(self, obj):
        """Check if subscription is in grace period"""
        return obj.in_grace_period()
    
    def get_days_remaining(self, obj):
        """Get days remaining in subscription period"""
        return obj.days_remaining()
    
    def get_effective_features(self, obj):
        """
        Get effective features for this subscription.
        Considers per-user overrides for Custom plans.
        
        Returns:
            list: List of enabled feature objects
        """
        enabled_features = obj._get_enabled_features()
        return FeatureSerializer(enabled_features, many=True).data
    
    def validate(self, attrs):
        """
        Validate subscription creation/update.
        """
        request = self.context.get('request')
        
        # Validate user role (restaurant owners only)
        if request and hasattr(request, 'user'):
            user = request.user
            if not hasattr(user, 'role') or user.role != 2:
                raise serializers.ValidationError({
                    'user': 'Only restaurant owners can have subscriptions.'
                })
        
        # Validate payment for paid plans
        plan = attrs.get('plan')
        payment_method_id = attrs.get('payment_method_id')
        
        if plan and not plan.is_free_plan():
            if not self.instance and not payment_method_id:
                raise serializers.ValidationError({
                    'payment_method_id': 'Payment method is required for paid subscriptions.'
                })
        
        # Remove payment_method_id from attrs (it's not a model field)
        if 'payment_method_id' in attrs:
            del attrs['payment_method_id']
        
        return attrs
    
    def validate_plan_id(self, value):
        """Validate plan selection"""
        if not value.is_active:
            raise serializers.ValidationError('Selected plan is not available.')
        return value


class UserSubscriptionCreateSerializer(serializers.Serializer):
    """
    Serializer specifically for creating subscriptions via API.
    Handles Stripe integration.
    """
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        help_text="ID of the subscription plan"
    )
    payment_method_id = serializers.CharField(
        required=False,
        help_text="Stripe payment method ID (required for paid plans)"
    )
    
    def validate(self, attrs):
        """Validate subscription creation"""
        plan = attrs['plan_id']
        payment_method_id = attrs.get('payment_method_id')
        
        # Validate payment for paid plans
        if not plan.is_free_plan() and not payment_method_id:
            raise serializers.ValidationError({
                'payment_method_id': 'Payment method is required for paid subscriptions.'
            })
        
        # Validate Free plan doesn't require payment
        if plan.is_free_plan() and payment_method_id:
            raise serializers.ValidationError({
                'payment_method_id': 'Free plan does not require payment method.'
            })
        
        return attrs


class UserSubscriptionUpgradeSerializer(serializers.Serializer):
    """
    Serializer for upgrading/downgrading subscription plans.
    """
    new_plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        help_text="ID of the new subscription plan"
    )
    payment_method_id = serializers.CharField(
        required=False,
        help_text="Stripe payment method ID (if upgrading to paid plan)"
    )
    
    def validate(self, attrs):
        """Validate plan upgrade"""
        new_plan = attrs['new_plan_id']
        payment_method_id = attrs.get('payment_method_id')
        
        # Validate payment for paid plans
        if not new_plan.is_free_plan() and not payment_method_id:
            # Check if user already has a payment method on file
            request = self.context.get('request')
            if request and hasattr(request.user, 'subscription'):
                subscription = request.user.subscription
                if not subscription.stripe_customer_id:
                    raise serializers.ValidationError({
                        'payment_method_id': 'Payment method is required for paid subscriptions.'
                    })
        
        return attrs
