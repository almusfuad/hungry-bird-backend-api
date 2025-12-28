from django.db import models
from hungryBird.baseModels import TimeStampedModel, LocationModel

# Create your models here.
class Restaurant(TimeStampedModel, LocationModel):
    owner = models.ForeignKey(
        'authUser.User', on_delete=models.CASCADE,
        limit_choices_to={'role': 2},
        related_name='restaurants'
    )
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    drivers = models.ManyToManyField(
        'authUser.User',
        limit_choices_to={'role': 3},
        related_name='assigned_restaurants',
        blank=True
    )


    def assign_driver(self, order):
        # Assign driver with no pending order
        available_drivers = self.drivers.filter(
            role = 3,
        ).exclude(
            deliveries__status__in=[3,4] # Exclude drivers with 'Ready for Pickup' or 'Out for Delivery' orders
        ).order_by('?') # Random order to distribute assignments fairly
        if available_drivers.exists():
            driver = available_drivers.first()
            order.driver = driver
            order.save()
            return driver
        return None


    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Restaurant'
        verbose_name_plural = 'Restaurants'
        ordering = ['name']





class MenuItem(TimeStampedModel):
    CATEGORY_CHOICES = [
        ('APP', 'Appetizer'),
        ('SOUP', 'Soup'),
        ('SAL', 'Salad'),
        ('SNK', 'Snack'),
        ('MAIN', 'Main Course'),
        ('SPEC', 'Specialty'),
        ('SIDE', 'Side Dish'),
        ('BRK', 'Breakfast'),
        ('VEG', 'Vegetarian'),
        ('VGN', 'Vegan'),
        ('KID', 'Kids Menu'),
        ('DES', 'Dessert'),
        ('BAK', 'Bakery & Pastry'),
    ]


    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)


    def __str__(self):
        return f"{self.name} - {self.restaurant.name}"
    


    class Meta:
        verbose_name = 'Menu Item'
        verbose_name_plural = 'Menu Items'
        ordering = ['name']


class AddOn(TimeStampedModel):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='add_ons')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.menu_item.name})"
    
