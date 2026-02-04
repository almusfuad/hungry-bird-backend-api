from django.contrib import admin
from subscriptions.models import UserSubscription
from .inlines import UserSubscriptionFeatureInline


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
