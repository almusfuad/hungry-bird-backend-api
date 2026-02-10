from django.db import models
from django.core.validators import MinValueValidator
from hungryBird.baseModels import TimeStampedModel


class SubscriptionPlan(TimeStampedModel):
    """
    Subscription plans available for restaurant owners.
    Examples: Free, Regular, Custom
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Plan name (e.g., Free, Regular, Custom)"
    )
    stripe_price_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Stripe Price ID (null for Free plan)"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text="Monthly subscription price in USD"
    )
    duration_days = models.PositiveIntegerField(
        default=30,
        help_text="Subscription duration in days (typically 30 for monthly)"
    )
    description = models.TextField(
        blank=True,
        help_text="Plan description and benefits"
    )
    grace_period_days = models.PositiveIntegerField(
        default=3,
        help_text="Days of grace period after payment failure before downgrading"
    )
    trial_days = models.PositiveIntegerField(
        default=0,
        help_text="Number of days for trial period (0 for no trial)"
    )

    class Meta:
        db_table = 'subscription_plans'
        ordering = ['price']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        return f"{self.name} (${self.price}/month)"

    def is_free_plan(self):
        """Check if this is the Free plan"""
        return self.price == 0 or self.name.lower() == 'free'
