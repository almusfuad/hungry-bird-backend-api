from django.db import models
from django.db.models import Q, CheckConstraint, UniqueConstraint
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from hungryBird.baseModels import TimeStampedModel
import fnmatch
import logging

logger = logging.getLogger('subscriptions')


class UserSubscription(TimeStampedModel):
    """
    User subscriptions for restaurant owners.
    Automatically assigns Free plan to new restaurant owners.
    """
    
    # Status choices
    STATUS_ACTIVE = 0
    STATUS_PAST_DUE = 1
    STATUS_CANCELLED = 2
    STATUS_EXPIRED = 3
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAST_DUE, 'Past Due'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_EXPIRED, 'Expired'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription',
        limit_choices_to={'role': 2},  # Restaurant owners only
        help_text="Restaurant owner user"
    )
    plan = models.ForeignKey(
        'subscriptions.SubscriptionPlan',
        on_delete=models.PROTECT,
        related_name='subscriptions',
        help_text="Subscription plan"
    )
    stripe_subscription_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Stripe subscription ID"
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Stripe customer ID"
    )
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        help_text="Subscription status"
    )
    current_period_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Current billing period start"
    )
    current_period_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Current billing period end (null for Free plan)"
    )
    grace_period_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Grace period end date after payment failure"
    )
    auto_renew = models.BooleanField(
        default=True,
        help_text="Whether subscription auto-renews"
    )

    class Meta:
        db_table = 'user_subscriptions'
        ordering = ['-created_at']
        verbose_name = 'User Subscription'
        verbose_name_plural = 'User Subscriptions'

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        """
        Override save to auto-assign Free plan to new restaurant owners.
        No signals used - database-level validation only.
        """
        # Auto-assign Free plan for new subscriptions
        if not self.pk and not UserSubscription.objects.filter(user=self.user).exists():
            # Check if user is restaurant owner
            if hasattr(self.user, 'role') and self.user.role == 2:
                # If no plan specified, assign Free plan
                if not self.plan_id:
                    from subscriptions.models import SubscriptionPlan
                    try:
                        free_plan = SubscriptionPlan.objects.get(name='Free')
                        self.plan = free_plan
                        self.status = self.STATUS_ACTIVE
                        self.current_period_start = timezone.now()
                        # Free plan has no end date (perpetual)
                        self.current_period_end = None
                        logger.info(f"Auto-assigned Free plan to user {self.user.id}")
                    except SubscriptionPlan.DoesNotExist:
                        logger.warning(f"Free plan does not exist. Cannot auto-assign to user {self.user.id}")
        
        super().save(*args, **kwargs)

    def is_expired(self):
        """
        Check if subscription is expired.
        
        Returns:
            bool: True if subscription is expired
        """
        if self.plan.is_free_plan():
            return False  # Free plan never expires
        
        if self.status == self.STATUS_EXPIRED:
            return True
        
        # Check if grace period has ended
        if self.status == self.STATUS_PAST_DUE and self.grace_period_end:
            return timezone.now() > self.grace_period_end
        
        # Check if period has ended and not auto-renewing
        if self.current_period_end and not self.auto_renew:
            return timezone.now() > self.current_period_end
        
        return False

    def in_grace_period(self):
        """
        Check if subscription is in grace period.
        
        Returns:
            bool: True if in grace period
        """
        if self.status != self.STATUS_PAST_DUE:
            return False
        
        if not self.grace_period_end:
            return False
        
        return timezone.now() <= self.grace_period_end

    def apply_grace_period(self):
        """
        Apply grace period to subscription after payment failure.
        Sets grace_period_end based on plan's grace_period_days.
        """
        self.status = self.STATUS_PAST_DUE
        self.grace_period_end = timezone.now() + timedelta(days=self.plan.grace_period_days)
        self.save(update_fields=['status', 'grace_period_end', 'updated_at'])
        logger.info(f"Applied grace period to subscription {self.id} until {self.grace_period_end}")

    def has_feature(self, feature_name):
        """
        Check if user has access to a specific feature.
        Considers per-user overrides for Custom plans.
        
        Args:
            feature_name (str): Name of the feature to check
            
        Returns:
            bool: True if user has access to the feature
        """
        # Check if subscription is active or in grace period
        if self.is_expired() and not self.in_grace_period():
            return False
        
        # First check for user-specific overrides
        user_override = self.usersubscriptionfeature_set.filter(
            feature__name=feature_name
        ).first()
        
        if user_override:
            return user_override.is_enabled
        
        # Fall back to plan's default features
        return self.plan.planfeature_set.filter(
            feature__name=feature_name,
            is_enabled=True
        ).exists()

    def has_url_access(self, url_path):
        """
        Check if user has access to a specific URL path.
        Matches against feature URL patterns using fnmatch.
        
        Args:
            url_path (str): URL path to check (e.g., 'restaurant/menu/create')
            
        Returns:
            bool: True if user has access to the URL
        """
        # Check if subscription is active or in grace period
        if self.is_expired() and not self.in_grace_period():
            return False
        
        # Get all enabled features (considering overrides)
        enabled_features = self._get_enabled_features()
        
        # Check if URL matches any enabled feature's patterns
        for feature in enabled_features:
            patterns = feature.get_patterns_list()
            for pattern in patterns:
                if fnmatch.fnmatch(url_path, pattern):
                    return True
        
        return False

    def _get_enabled_features(self):
        """
        Get all enabled features for this subscription.
        Considers user-specific overrides.
        
        Returns:
            QuerySet: Enabled Feature objects
        """
        from subscriptions.models import Feature
        
        # Get features with user overrides
        overridden_feature_ids = list(
            self.usersubscriptionfeature_set.values_list('feature_id', flat=True)
        )
        
        # Get overridden features that are enabled
        enabled_override_ids = list(
            self.usersubscriptionfeature_set.filter(
                is_enabled=True
            ).values_list('feature_id', flat=True)
        )
        
        # Get plan features that are enabled and not overridden
        enabled_plan_feature_ids = list(
            self.plan.planfeature_set.filter(
                is_enabled=True
            ).exclude(
                feature_id__in=overridden_feature_ids
            ).values_list('feature_id', flat=True)
        )
        
        # Combine both lists
        all_enabled_feature_ids = enabled_override_ids + enabled_plan_feature_ids
        
        return Feature.objects.filter(id__in=all_enabled_feature_ids)

    def days_remaining(self):
        """
        Calculate days remaining in subscription period.
        
        Returns:
            int or None: Days remaining, or None for Free plan
        """
        if self.plan.is_free_plan() or not self.current_period_end:
            return None
        
        delta = self.current_period_end - timezone.now()
        return max(0, delta.days)
