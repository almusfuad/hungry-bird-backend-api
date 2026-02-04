from django.db import models
from django.db.models import UniqueConstraint
from hungryBird.baseModels import TimeStampedModel


class PlanFeature(TimeStampedModel):
    """
    Through model connecting subscription plans to features.
    Allows enabling/disabling features per plan.
    """
    plan = models.ForeignKey(
        'subscriptions.SubscriptionPlan',
        on_delete=models.CASCADE,
        related_name='planfeature_set'
    )
    feature = models.ForeignKey(
        'subscriptions.Feature',
        on_delete=models.CASCADE,
        related_name='planfeature_set'
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Whether this feature is enabled for this plan"
    )

    class Meta:
        db_table = 'subscription_plan_features'
        ordering = ['plan', 'feature']
        verbose_name = 'Plan Feature'
        verbose_name_plural = 'Plan Features'
        constraints = [
            UniqueConstraint(
                fields=['plan', 'feature'],
                name='unique_plan_feature'
            )
        ]

    def __str__(self):
        status = "✓" if self.is_enabled else "✗"
        return f"{status} {self.plan.name} - {self.feature.name}"
