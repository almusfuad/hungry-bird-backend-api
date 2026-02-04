from django.contrib import admin
from django.db.models import Count
from subscriptions.models import (
    SubscriptionPlan,
    Feature,
    PlanFeature,
    UserSubscription,
    UserSubscriptionFeature
)


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
            'fields': ('stripe_price_id', 'price', 'duration_days')
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


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    """
    Admin interface for features with URL pattern management.
    """
    list_display = [
        'name',
        'description',
        'pattern_preview',
        'is_active',
        'created_at'
    ]
    
    list_filter = ['is_active', 'created_at']
    
    search_fields = ['name', 'description', 'url_patterns']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Feature Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('URL Patterns', {
            'fields': ('url_patterns',),
            'description': 'Enter one URL pattern per line. Use glob patterns like restaurant/*, order/create, pos/*'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Customize form field for url_patterns to use textarea"""
        if db_field.name == 'url_patterns':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(attrs={'rows': 5, 'cols': 80})
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    
    def pattern_preview(self, obj):
        """Display preview of URL patterns"""
        if not obj.url_patterns:
            return '-'
        patterns = obj.url_patterns.strip()
        if len(patterns) > 50:
            return patterns[:50] + '...'
        return patterns
    pattern_preview.short_description = 'URL Patterns'


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    """
    Admin interface for user subscriptions with feature overrides.
    """
    inlines = [UserSubscriptionFeatureInline]
    
    list_display = [
        'user',
        'plan',
        'status_display',
        'current_period_end',
        'auto_renew',
        'is_active',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'plan',
        'auto_renew',
        'is_active',
        'created_at'
    ]
    
    search_fields = [
        'user__username',
        'user__phone_number',
        'user__email',
        'stripe_subscription_id',
        'stripe_customer_id'
    ]
    
    readonly_fields = [
        'stripe_subscription_id',
        'stripe_customer_id',
        'current_period_start',
        'current_period_end',
        'grace_period_end',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('User & Plan', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Stripe Information', {
            'fields': ('stripe_subscription_id', 'stripe_customer_id')
        }),
        ('Billing Period', {
            'fields': (
                'current_period_start',
                'current_period_end',
                'grace_period_end',
                'auto_renew'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['sync_with_stripe_action']
    
    def status_display(self, obj):
        """Display subscription status with color coding"""
        status_colors = {
            0: '🟢',  # Active
            1: '🟡',  # Past Due
            2: '🟠',  # Cancelled
            3: '🔴',  # Expired
        }
        icon = status_colors.get(obj.status, '⚪')
        return f"{icon} {obj.get_status_display()}"
    status_display.short_description = 'Status'
    
    def sync_with_stripe_action(self, request, queryset):
        """
        Admin action to sync selected subscriptions with Stripe.
        Triggers Celery task for each subscription.
        """
        # Import here to avoid circular imports
        try:
            from subscriptions.tasks.sync import sync_stripe_status
            
            synced_count = 0
            for subscription in queryset:
                if subscription.stripe_subscription_id:
                    sync_stripe_status.delay(subscription.id)
                    synced_count += 1
            
            self.message_user(
                request,
                f'Queued {synced_count} subscription(s) for Stripe sync.'
            )
        except ImportError:
            self.message_user(
                request,
                'Celery tasks not yet configured. Sync unavailable.',
                level='warning'
            )
    
    sync_with_stripe_action.short_description = 'Sync with Stripe'
