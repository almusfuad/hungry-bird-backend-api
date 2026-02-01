from django.contrib import admin
from .models import Cart, CartItem, CartAddOn


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'restaurant', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'restaurant')
    search_fields = ('customer__username', 'restaurant__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Cart Information', {
            'fields': ('customer', 'restaurant', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'menu_item', 'quantity', 'get_item_total')
    list_filter = ('created_at', 'cart__restaurant')
    search_fields = ('cart__customer__username', 'menu_item__name')
    readonly_fields = ('created_at', 'updated_at', 'get_item_total')
    fieldsets = (
        ('Item Information', {
            'fields': ('cart', 'menu_item', 'quantity')
        }),
        ('Totals', {
            'fields': ('get_item_total',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_item_total(self, obj):
        return obj.get_item_total()
    get_item_total.short_description = 'Item Total'


@admin.register(CartAddOn)
class CartAddOnAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart_item', 'add_on', 'quantity', 'get_add_on_total')
    list_filter = ('created_at', 'cart_item__cart__restaurant')
    search_fields = ('cart_item__cart__customer__username', 'add_on__name')
    readonly_fields = ('created_at', 'updated_at', 'get_add_on_total')
    fieldsets = (
        ('AddOn Information', {
            'fields': ('cart_item', 'add_on', 'quantity')
        }),
        ('Totals', {
            'fields': ('get_add_on_total',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_add_on_total(self, obj):
        return obj.get_add_on_total()
    get_add_on_total.short_description = 'AddOn Total'

