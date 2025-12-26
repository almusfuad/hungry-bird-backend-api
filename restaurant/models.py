from django.db import models


# Create your models here.
class TimeStampedModel(models.Model):
    '''Abstract Base model'''
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class Restaurant(TimeStampedModel):
    owner = models.ForeignKey(
        'authUser.User', on_delete=models.CASCADE,
        limit_choices_to={'role': 2},
        related_name='restaurants'
    )
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    drivers = models.ManyToManyField(
        'authUser.User',
        limit_choices_to={'role': 3},
        related_name='assigned_restaurants',
        blank=True
    )


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
    
