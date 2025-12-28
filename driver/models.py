from django.db import models
from hungryBird.baseModels import TimeStampedModel, LocationModel

# Create your models here.
class DriverProfile(TimeStampedModel, LocationModel):
    user = models.OneToOneField(
        'authUser.User', on_delete=models.CASCADE,
        limit_choices_to={'role': 3},
        related_name='driver_profile'
    )
    license_number = models.CharField(max_length=50)
    vehicle_details = models.TextField()

    def __str__(self):
        return f"Driver Profile: {self.user.username}"
    
    class Meta:
        verbose_name = 'Driver Profile'
        verbose_name_plural = 'Driver Profiles'
        ordering = ['user__username']
    
class DriverAvailability(TimeStampedModel):
    STATUS_CHOICES = [
        (0, 'Unavailable'),
        (1, 'Available'),
        (2, 'On Delivery'),
    ]

    driver = models.OneToOneField(
        'authUser.User', on_delete=models.CASCADE,
        limit_choices_to={'role': 3},
        related_name='current_availability' 
    )
    order = models.ForeignKey(
        'order.Order', on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='assigned_driver'
    )
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=1)


    def __str__(self):
        return f"Driver Availability: {self.driver.username} - {self.get_status_display()}"
    

    class Meta:
        verbose_name = 'Driver Availability'
        verbose_name_plural = 'Driver Availabilities'
        ordering = ['-updated_at']