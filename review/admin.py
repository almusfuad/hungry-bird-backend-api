from django.contrib import admin
from review.models import Review, ReviewResponse, HelpfulVote


class ReviewResponseInline(admin.StackedInline):
    """
    Inline admin for ReviewResponse to display under Review.
    """
    model = ReviewResponse
    extra = 0
    can_delete = False
    fields = ['owner', 'response_text', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Admin configuration for Review model.
    """
    list_display = [
        'id',
        'customer',
        'restaurant',
        'menu_item',
        'rating',
        'is_anonymous',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'rating',
        'is_anonymous',
        'is_active',
        'created_at',
        'restaurant'
    ]
    search_fields = [
        'customer__username',
        'restaurant__name',
        'menu_item__name',
        'comment'
    ]
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ReviewResponseInline]
    fieldsets = (
        ('Review Information', {
            'fields': (
                'customer',
                'order',
                'restaurant',
                'menu_item',
                'rating',
                'comment',
                'is_anonymous'
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ReviewResponse)
class ReviewResponseAdmin(admin.ModelAdmin):
    """
    Admin configuration for ReviewResponse model.
    Responses are immutable, so no edit/delete capabilities.
    """
    list_display = [
        'id',
        'review',
        'owner',
        'created_at'
    ]
    list_filter = ['created_at']
    search_fields = [
        'owner__username',
        'review__restaurant__name',
        'response_text'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    def has_change_permission(self, request, obj=None):
        """
        Disable editing of responses (immutable).
        """
        return False
    
    def has_delete_permission(self, request, obj=None):
        """
        Disable deletion of responses (immutable).
        """
        return False


@admin.register(HelpfulVote)
class HelpfulVoteAdmin(admin.ModelAdmin):
    """
    Admin configuration for HelpfulVote model.
    """
    list_display = [
        'id',
        'review',
        'user',
        'is_helpful',
        'created_at'
    ]
    list_filter = [
        'is_helpful',
        'created_at'
    ]
    search_fields = [
        'user__username',
        'review__comment'
    ]
    readonly_fields = ['created_at', 'updated_at']

