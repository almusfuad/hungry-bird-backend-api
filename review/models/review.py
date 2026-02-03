from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Q
from hungryBird.baseModels import TimeStampedModel


class Review(TimeStampedModel):
    """
    Model to store customer reviews for restaurants and menu items.
    Customers can review either a restaurant or a specific menu item from an order.
    """
    customer = models.ForeignKey(
        'authUser.User',
        on_delete=models.DO_NOTHING,
        related_name='reviews',
        limit_choices_to={'role': 1}
    )
    order = models.ForeignKey(
        'order.Order',
        on_delete=models.DO_NOTHING,
        related_name='reviews'
    )
    restaurant = models.ForeignKey(
        'restaurant.Restaurant',
        on_delete=models.DO_NOTHING,
        related_name='reviews'
    )
    menu_item = models.ForeignKey(
        'restaurant.MenuItem',
        on_delete=models.DO_NOTHING,
        related_name='reviews',
        null=True,
        blank=True
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[
            MinValueValidator(1.00),
            MaxValueValidator(5.00)
        ]
    )
    comment = models.TextField()
    is_anonymous = models.BooleanField(default=False)

    class Meta:
        unique_together = [('customer', 'order', 'restaurant', 'menu_item')]
        constraints = [
            models.CheckConstraint(
                check=Q(rating__gte=1.00, rating__lte=5.00),
                name='rating_range_check'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        item_name = self.menu_item.name if self.menu_item else self.restaurant.name
        return f"Review by {self.customer.username} for {item_name} - {self.rating}"

    def can_edit(self):
        """
        Check if the review can be edited.
        Reviews can only be edited within 6 hours of creation and must be active.
        """
        if not self.is_active:
            return False
        time_diff = timezone.now() - self.created_at
        return time_diff <= timezone.timedelta(hours=6)

    def get_display_name(self):
        """
        Get the display name for the reviewer.
        Returns 'Anonymous' if the review is anonymous, otherwise returns username.
        """
        return 'Anonymous' if self.is_anonymous else self.customer.username

    def get_helpful_count(self):
        """
        Get the count of helpful votes for this review.
        """
        return self.helpful_votes.filter(is_helpful=True).count()
