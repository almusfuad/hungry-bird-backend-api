from django.contrib import admin
from django.db.models import Count
from subscriptions.models import SubscriptionPlan
from .inlines import PlanFeatureInline


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    """
    Admin interface for subscription plans with feature management.
    """
    inlines = [PlanFeatureInline]
    
    list_display = [
        'name',
        'price',
        'duration_days',
        'trial_days',
        'grace_period_days',
        'feature_count',
        'is_active',
        'created_at'
    ]
    
    list_filter = ['is_active', 'created_at', 'price']
    
    search_fields = ['name', 'description']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Stripe & Pricing', {
            'fields': ('stripe_price_id', 'price', 'duration_days', 'trial_days')
        }),
        ('Configuration', {
            'fields': ('grace_period_days', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def feature_count(self, obj):
        """Display count of enabled features for this plan"""
        return obj.planfeature_set.filter(is_enabled=True).count()
    feature_count.short_description = 'Active Features'
    
    def get_queryset(self, request):
        """Optimize queryset with feature count annotation"""
        qs = super().get_queryset(request)
        return qs.annotate(
            _feature_count=Count('planfeature', filter=admin.models.Q(planfeature__is_enabled=True))
        )
