from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    ROLE_CHOICES = (
        (1, 'Customer'),
        (2, 'Restaurant Owner'),
        (3, 'Driver'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=1)
    phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True)

    def __str__(self):
        return self.username


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

        