from django.contrib import admin
from subscriptions.models import PlanFeature, UserSubscriptionFeature


class PlanFeatureInline(admin.TabularInline):
    """
    Inline admin for managing features within a subscription plan.
    Shows all features with enable/disable toggles.
    """
    model = PlanFeature
    extra = 0
    can_delete = False
    fields = ['feature', 'is_enabled']
    readonly_fields = []
    verbose_name = 'Feature'
    verbose_name_plural = 'Plan Features'


class UserSubscriptionFeatureInline(admin.TabularInline):
    """
    Inline admin for per-user feature overrides.
    Only applicable for Custom plan subscriptions.
    """
    model = UserSubscriptionFeature
    extra = 0
    fields = ['feature', 'is_enabled', 'created_at']
    readonly_fields = ['created_at']
    verbose_name = 'Feature Override'
    verbose_name_plural = 'User Feature Overrides'
