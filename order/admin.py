from django.contrib import admin
from order.models import Order, OrderItem, OrderAddOn

# Register your models here.
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderAddOn)