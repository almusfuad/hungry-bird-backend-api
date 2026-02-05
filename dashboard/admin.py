from django.contrib import admin
from .models import OrderStatusTransition, CSVExportLog


@admin.register(OrderStatusTransition)
class OrderStatusTransitionAdmin(admin.ModelAdmin):
    list_display = ('order', 'from_status', 'to_status', 'transitioned_at', 'is_backfilled')
    list_filter = ('is_backfilled', 'to_status', 'transitioned_at')
    search_fields = ('order__id',)
    readonly_fields = ('transitioned_at',)


@admin.register(CSVExportLog)
class CSVExportLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'resource_type', 'exported_at')
    list_filter = ('resource_type', 'exported_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('exported_at',)
