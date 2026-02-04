from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from hungryBird.permissions import IsRestaurantOwner
from subscriptions.models import UserSubscription, SubscriptionPlan
from subscriptions.serializers import (
    UserSubscriptionSerializer,
    UserSubscriptionCreateSerializer,
    UserSubscriptionUpgradeSerializer,
    UserSubscriptionFeatureSerializer
)
from payment.subscription import SubscriptionService
import logging

logger = logging.getLogger('subscriptions')


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user subscriptions.
    Only accessible by restaurant owners for their own subscriptions.
    """
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated, IsRestaurantOwner]
    
    def get_queryset(self):
        """Filter queryset to current user's subscription only"""
        if self.request.user.is_authenticated:
            return UserSubscription.objects.filter(
                user=self.request.user
            ).select_related('plan').prefetch_related(
                'plan__planfeature_set__feature',
                'usersubscriptionfeature_set__feature'
            )
        return UserSubscription.objects.none()
    
    def list(self, request, *args, **kwargs):
        """
        Get current user's subscription.
        Returns single object instead of list.
        """
        try:
            subscription = self.get_queryset().first()
            if subscription:
                serializer = self.get_serializer(subscription)
                return Response(serializer.data)
            else:
                return Response(
                    {'detail': 'No subscription found.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.error(f"Error retrieving subscription for user {request.user.id}: {str(e)}")
            return Response(
                {'detail': 'Error retrieving subscription.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        """
        Create a new subscription for the user.
        
        Request body:
        {
            "plan_id": 1,
            "payment_method_id": "pm_xxx" (required for paid plans)
        }
        """
        # Check if user already has a subscription
        if hasattr(request.user, 'subscription'):
            return Response(
                {'detail': 'User already has an active subscription. Use upgrade endpoint to change plans.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate input
        serializer = UserSubscriptionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        plan = serializer.validated_data['plan_id']
        payment_method_id = serializer.validated_data.get('payment_method_id')
        
        try:
            with transaction.atomic():
                # For Free plan, just create the subscription
                if plan.is_free_plan():
                    subscription = UserSubscription.objects.create(
                        user=request.user,
                        plan=plan,
                        status=UserSubscription.STATUS_ACTIVE
                    )
                    logger.info(f"Created Free subscription for user {request.user.id}")
                
                # For paid plans, create Stripe subscription
                else:
                    # Create or get Stripe customer
                    if not request.user.stripe_customer_id:
                        customer_id = SubscriptionService.create_stripe_customer(request.user)
                        request.user.stripe_customer_id = customer_id
                        request.user.save(update_fields=['stripe_customer_id'])
                    else:
                        customer_id = request.user.stripe_customer_id
                    
                    # Create Stripe subscription
                    stripe_subscription = SubscriptionService.create_subscription(
                        customer_id=customer_id,
                        price_id=plan.stripe_price_id,
                        payment_method_id=payment_method_id
                    )
                    
                    # Create local subscription record
                    subscription = UserSubscription.objects.create(
                        user=request.user,
                        plan=plan,
                        stripe_subscription_id=stripe_subscription['id'],
                        stripe_customer_id=customer_id,
                        status=UserSubscription.STATUS_ACTIVE,
                        auto_renew=True
                    )
                    
                    logger.info(
                        f"Created {plan.name} subscription for user {request.user.id} "
                        f"with Stripe subscription {stripe_subscription['id']}"
                    )
                
                # Return subscription data
                response_serializer = UserSubscriptionSerializer(subscription)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Error creating subscription for user {request.user.id}: {str(e)}")
            return Response(
                {'detail': f'Failed to create subscription: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def upgrade(self, request, pk=None):
        """
        Upgrade or downgrade subscription plan.
        
        Request body:
        {
            "new_plan_id": 2,
            "payment_method_id": "pm_xxx" (optional if already have payment method)
        }
        """
        subscription = self.get_object()
        
        # Validate input
        serializer = UserSubscriptionUpgradeSerializer(
            data=request.data,
            context={'request': request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        new_plan = serializer.validated_data['new_plan_id']
        payment_method_id = serializer.validated_data.get('payment_method_id')
        
        # Can't "upgrade" to same plan
        if subscription.plan.id == new_plan.id:
            return Response(
                {'detail': 'Already subscribed to this plan.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                old_plan = subscription.plan.name
                
                # Downgrade to Free plan
                if new_plan.is_free_plan():
                    # Cancel Stripe subscription if exists
                    if subscription.stripe_subscription_id:
                        SubscriptionService.cancel_subscription(
                            subscription.stripe_subscription_id,
                            at_period_end=True
                        )
                    
                    subscription.plan = new_plan
                    subscription.auto_renew = False
                    subscription.save()
                    
                    logger.info(f"Downgraded user {request.user.id} from {old_plan} to Free")
                
                # Upgrade to paid plan
                else:
                    # Create Stripe customer if needed
                    if not subscription.stripe_customer_id:
                        customer_id = SubscriptionService.create_stripe_customer(request.user)
                        request.user.stripe_customer_id = customer_id
                        request.user.save(update_fields=['stripe_customer_id'])
                        subscription.stripe_customer_id = customer_id
                    
                    # Update Stripe subscription
                    if subscription.stripe_subscription_id:
                        stripe_subscription = SubscriptionService.update_subscription(
                            subscription.stripe_subscription_id,
                            new_plan.stripe_price_id
                        )
                    else:
                        # Create new Stripe subscription
                        stripe_subscription = SubscriptionService.create_subscription(
                            customer_id=subscription.stripe_customer_id,
                            price_id=new_plan.stripe_price_id,
                            payment_method_id=payment_method_id
                        )
                        subscription.stripe_subscription_id = stripe_subscription['id']
                    
                    subscription.plan = new_plan
                    subscription.status = UserSubscription.STATUS_ACTIVE
                    subscription.auto_renew = True
                    subscription.save()
                    
                    logger.info(
                        f"Upgraded user {request.user.id} from {old_plan} to {new_plan.name}"
                    )
                
                # Return updated subscription
                response_serializer = UserSubscriptionSerializer(subscription)
                return Response(response_serializer.data)
                
        except Exception as e:
            logger.error(f"Error upgrading subscription for user {request.user.id}: {str(e)}")
            return Response(
                {'detail': f'Failed to upgrade subscription: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel subscription at period end.
        User retains access until current period ends.
        """
        subscription = self.get_object()
        
        # Can't cancel Free plan
        if subscription.plan.is_free_plan():
            return Response(
                {'detail': 'Cannot cancel Free plan.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Already cancelled
        if subscription.status == UserSubscription.STATUS_CANCELLED:
            return Response(
                {'detail': 'Subscription is already cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Cancel Stripe subscription at period end
            if subscription.stripe_subscription_id:
                SubscriptionService.cancel_subscription(
                    subscription.stripe_subscription_id,
                    at_period_end=True
                )
            
            # Update local subscription
            subscription.auto_renew = False
            subscription.status = UserSubscription.STATUS_CANCELLED
            subscription.save()
            
            logger.info(f"Cancelled subscription {subscription.id} for user {request.user.id}")
            
            # Return updated subscription
            response_serializer = UserSubscriptionSerializer(subscription)
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"Error cancelling subscription for user {request.user.id}: {str(e)}")
            return Response(
                {'detail': f'Failed to cancel subscription: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'])
    def toggle_feature(self, request, pk=None):
        """
        Toggle a specific feature on/off for Custom plan subscriptions.
        Only works for Custom plan with per-user feature overrides.
        
        Request body:
        {
            "feature_id": 1,
            "is_enabled": true
        }
        """
        subscription = self.get_object()
        
        # Only Custom plan allows feature toggling
        if subscription.plan.name.lower() != 'custom':
            return Response(
                {'detail': 'Feature toggling is only available for Custom plan.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate input
        serializer = UserSubscriptionFeatureSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        feature = serializer.validated_data['feature']
        is_enabled = serializer.validated_data['is_enabled']
        
        try:
            # Create or update feature override
            feature_override, created = subscription.usersubscriptionfeature_set.update_or_create(
                feature=feature,
                defaults={'is_enabled': is_enabled}
            )
            
            action_text = 'enabled' if is_enabled else 'disabled'
            logger.info(
                f"User {request.user.id} {action_text} feature {feature.name} "
                f"on subscription {subscription.id}"
            )
            
            # Return updated subscription
            response_serializer = UserSubscriptionSerializer(subscription)
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"Error toggling feature for user {request.user.id}: {str(e)}")
            return Response(
                {'detail': f'Failed to toggle feature: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
