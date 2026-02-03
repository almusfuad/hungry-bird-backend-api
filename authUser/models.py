from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from hungryBird.utils import validate_image_size
from hungryBird.baseModels import LocationModel
from restaurant.models import Restaurant

# Create your models here.
class User(AbstractUser, LocationModel):
    ROLE_CHOICES = (
        (0, 'Admin'),
        (1, 'Customer'),
        (2, 'Restaurant Owner'),
        (3, 'Driver'),
    )
    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICES, default=1)
    phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True)
    image = models.ImageField(upload_to='user_images/', blank=True, null=True)
    enable_review_notifications = models.BooleanField(default=True)


    # Group reverse accessor
    groups = models.ManyToManyField(
        'auth.group',
        related_name='authuser_groups', # Change from default userset
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='authuser_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


    def save(self, *args, **kwargs):
        if self.image:
            validation_result = validate_image_size(self.image, max_size_kb=512)
            if not validation_result['success']:
                raise ValidationError(f"Image validation failed: {validation_result['message']}")
        super().save(*args, **kwargs)




    def has_restaurant(self) -> bool:
        try:
            self.restaurant
            return True
        except Restaurant.DoesNotExist:
            return False
    


    def __str__(self):
        return self.username

        