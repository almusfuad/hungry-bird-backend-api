from django.contrib import admin
from .models import Restaurant, MenuItem, AddOn

# Register your models here.
admin.site.register(Restaurant)
admin.site.register(MenuItem)
admin.site.register(AddOn)