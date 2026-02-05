from django.contrib import admin
from .models import RecommendationLog


@admin.register(RecommendationLog)
class RecommendationLogAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'customer',
        'recommendation_type',
        'restaurant',
        'menu_item',
        'was_clicked',
        'created_at',
    ]
    list_filter = [
        'recommendation_type',
        'was_clicked',
        'created_at',
    ]
    search_fields = [
        'customer__username',
        'customer__email',
        'restaurant__name',
        'menu_item__name',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Recommendation Details', {
            'fields': ('recommendation_type', 'customer', 'restaurant', 'menu_item')
        }),
        ('Location Information', {
            'fields': ('user_latitude', 'user_longitude', 'search_radius')
        }),
        ('Interaction', {
            'fields': ('was_clicked', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Recommendation logs are created programmatically, not manually
        return False
