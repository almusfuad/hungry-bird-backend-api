from django.db import models


class TimeStampedModel(models.Model):
    '''Abstract Base model'''
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class LocationModel(models.Model):
    latitude = models.DecimalField(max_digits=9, 
            decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, 
            decimal_places=6, blank=True, null=True)
    
    class Meta:
        abstract = True
