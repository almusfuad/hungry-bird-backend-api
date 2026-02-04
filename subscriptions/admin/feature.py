from django.contrib import admin
from subscriptions.models import Feature


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
