from django.db import models
from django.core.exceptions import ValidationError
from datetime import datetime, time
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
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=1)
    manual_override = models.BooleanField(
        default=False,
        help_text='If True, driver manually set availability and auto-scheduling will not override it'
    )


    def __str__(self):
        return f"Driver Availability: {self.driver.username} - {self.get_status_display()}"
    

    class Meta:
        verbose_name = 'Driver Availability'
        verbose_name_plural = 'Driver Availabilities'
        ordering = ['-updated_at']


class DriverSchedule(TimeStampedModel):
    """Model for managing driver's weekly availability schedule.
    Allows multiple schedules per day for split shifts (e.g., lunch and dinner).
    """
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    driver = models.ForeignKey(
        'authUser.User', on_delete=models.CASCADE,
        limit_choices_to={'role': 3},
        related_name='schedules'
    )
    day_of_week = models.PositiveSmallIntegerField(
        choices=DAY_CHOICES,
        help_text='0=Monday, 1=Tuesday, ..., 6=Sunday'
    )
    start_time = models.TimeField(help_text='Start time for this schedule block')
    end_time = models.TimeField(help_text='End time for this schedule block')
    is_active = models.BooleanField(
        default=True,
        help_text='Set to False to temporarily disable this schedule without deleting'
    )
    
    def clean(self):
        """Validate that end_time is after start_time."""
        super().clean()
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError({
                    'end_time': 'End time must be after start time.'
                })
    
    def is_within_schedule(self, current_datetime):
        """Check if the given datetime falls within this schedule.
        
        Args:
            current_datetime: datetime object to check
            
        Returns:
            bool: True if datetime is within this schedule
        """
        if not self.is_active:
            return False
        
        # Check if day matches
        if current_datetime.weekday() != self.day_of_week:
            return False
        
        # Check if time is within range
        current_time = current_datetime.time()
        return self.start_time <= current_time <= self.end_time
    
    def __str__(self):
        return f"{self.driver.username} - {self.get_day_of_week_display()} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
    
    class Meta:
        verbose_name = 'Driver Schedule'
        verbose_name_plural = 'Driver Schedules'
        ordering = ['driver__username', 'day_of_week', 'start_time']
        unique_together = [('driver', 'day_of_week', 'start_time')]
        indexes = [
            models.Index(fields=['driver', 'day_of_week', 'is_active']),
        ]