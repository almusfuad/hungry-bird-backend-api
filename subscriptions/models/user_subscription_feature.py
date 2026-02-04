from django.db import models
from django.db.models import UniqueConstraint
from hungryBird.baseModels import TimeStampedModel


class UserSubscriptionFeature(TimeStampedModel):
    """
    Per-user feature overrides for Custom plan subscriptions.
    Allows toggling specific features on/off for individual users.
    """
    subscription = models.ForeignKey(
        'subscriptions.UserSubscription',
        on_delete=models.CASCADE,
        related_name='usersubscriptionfeature_set'
    )
    feature = models.ForeignKey(
        'subscriptions.Feature',
        on_delete=models.CASCADE,
        related_name='usersubscriptionfeature_set'
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Whether this feature is enabled for this specific user"
    )

    class Meta:
        db_table = 'subscription_user_features'
        ordering = ['subscription', 'feature']
        verbose_name = 'User Subscription Feature Override'
        verbose_name_plural = 'User Subscription Feature Overrides'
        constraints = [
            UniqueConstraint(
                fields=['subscription', 'feature'],
                name='unique_subscription_feature'
            )
        ]

    def __str__(self):
        status = "✓" if self.is_enabled else "✗"
        return f"{status} {self.subscription.user.username} - {self.feature.name}"
