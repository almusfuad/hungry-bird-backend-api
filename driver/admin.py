from django.contrib import admin
from .models import DriverProfile, DriverAvailability, DriverSchedule

# Register your models here.
admin.site.register(DriverProfile)
admin.site.register(DriverAvailability)
admin.site.register(DriverSchedule)
