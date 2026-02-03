from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count
from decimal import Decimal
from hungryBird.baseModels import TimeStampedModel, LocationModel
from hungryBird.utils import validate_image_size

# Create your models here.
class Restaurant(TimeStampedModel, LocationModel):
    owner = models.OneToOneField(
        'authUser.User', on_delete=models.SET_NULL, blank=True, null=True,
        limit_choices_to={'role': 2},
        related_name='restaurant'
    )
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    image = models.ImageField(upload_to='restaurant_images/', blank=True, null=True)
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

    def save(self, *args, **kwargs):
        """
        Override save method to validate image size before saving.
        Max size: 500KB
        """
        if self.image:
            validation_result = validate_image_size(self.image, max_size_kb=1024)
            if not validation_result['success']:
                raise ValidationError(f"Image validation failed: {validation_result['message']}")
        
        super().save(*args, **kwargs)


    def get_average_rating(self):
        """
        Calculate average rating for restaurant-level reviews (not menu items).
        Returns Decimal or None.
        """
        result = self.reviews.filter(
            is_active=True,
            menu_item__isnull=True
        ).aggregate(avg=Avg('rating'))
        return result['avg']

    def get_total_reviews(self):
        """
        Get total count of active restaurant-level reviews.
        """
        return self.reviews.filter(
            is_active=True,
            menu_item__isnull=True
        ).count()

    def get_rating_breakdown(self):
        """
        Get rating breakdown showing count for each rating level (1-5).
        Returns dict: {5: count, 4: count, 3: count, 2: count, 1: count}
        """
        reviews = self.reviews.filter(
            is_active=True,
            menu_item__isnull=True
        ).values('rating').annotate(count=Count('id')).order_by('rating')
        
        # Initialize all ratings to 0
        breakdown = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        
        # Group ratings by whole number (floor)
        for item in reviews:
            rating = int(item['rating'])  # Convert to int to group (4.5 -> 4, 4.2 -> 4)
            if rating in breakdown:
                breakdown[rating] += item['count']
        
        return breakdown

    @property
    def average_rating(self):
        """
        Property to get average rating rounded to 2 decimal places.
        Returns Decimal('0.00') if no reviews.
        """
        avg = self.get_average_rating()
        if avg is None:
            return Decimal('0.00')
        return round(Decimal(str(avg)), 2)

    @property
    def total_reviews(self):
        """
        Property to get total review count.
        """
        return self.get_total_reviews()

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
    image = models.ImageField(upload_to='menu_item_images/', blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)


    def save(self, *args, **kwargs):
        """
        Override save method to validate image size before saving.
        Max size: 1024KB
        """
        if self.image:
            validation_result = validate_image_size(self.image, max_size_kb=1024)
            if not validation_result['success']:
                raise ValidationError(f"Image validation failed: {validation_result['message']}")
        
        super().save(*args, **kwargs)


    def get_average_rating(self):
        """
        Calculate average rating for this menu item.
        Returns Decimal or None.
        """
        result = self.reviews.filter(is_active=True).aggregate(avg=Avg('rating'))
        return result['avg']

    def get_total_reviews(self):
        """
        Get total count of active reviews for this menu item.
        """
        return self.reviews.filter(is_active=True).count()

    def get_rating_breakdown(self):
        """
        Get rating breakdown showing count for each rating level (1-5).
        Returns dict: {5: count, 4: count, 3: count, 2: count, 1: count}
        """
        reviews = self.reviews.filter(
            is_active=True
        ).values('rating').annotate(count=Count('id')).order_by('rating')
        
        # Initialize all ratings to 0
        breakdown = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        
        # Group ratings by whole number (floor)
        for item in reviews:
            rating = int(item['rating'])  # Convert to int to group (4.5 -> 4, 4.2 -> 4)
            if rating in breakdown:
                breakdown[rating] += item['count']
        
        return breakdown

    @property
    def average_rating(self):
        """
        Property to get average rating rounded to 2 decimal places.
        Returns Decimal('0.00') if no reviews.
        """
        avg = self.get_average_rating()
        if avg is None:
            return Decimal('0.00')
        return round(Decimal(str(avg)), 2)

    @property
    def total_reviews(self):
        """
        Property to get total review count.
        """
        return self.get_total_reviews()

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
    
