from django.db import models
from hungryBird.baseModels import TimeStampedModel
from authUser.models import User
from restaurant.models import Restaurant, MenuItem


class RecommendationLog(TimeStampedModel):
    """
    Model to track recommendation impressions and interactions.
    Helps analyze recommendation effectiveness for future improvements.
    """
    
    NEARBY_RESTAURANT = 1
    POPULAR_ITEM = 2
    PERSONALIZED = 3
    
    RECOMMENDATION_TYPE_CHOICES = [
        (NEARBY_RESTAURANT, 'Nearby Restaurant'),
        (POPULAR_ITEM, 'Popular Item'),
        (PERSONALIZED, 'Personalized'),
    ]
    
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recommendation_logs',
        null=True,
        blank=True,
        limit_choices_to={'role': 1},
        help_text='Customer who received the recommendation. Null for anonymous users.'
    )
    recommendation_type = models.IntegerField(
        choices=RECOMMENDATION_TYPE_CHOICES,
        help_text='Type of recommendation shown to the user'
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='recommendation_logs',
        null=True,
        blank=True,
        help_text='Restaurant that was recommended (if applicable)'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='recommendation_logs',
        null=True,
        blank=True,
        help_text='Menu item that was recommended (if applicable)'
    )
    user_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text='User latitude at the time of recommendation'
    )
    user_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text='User longitude at the time of recommendation'
    )
    search_radius = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.0,
        help_text='Search radius in kilometers used for the recommendation'
    )
    was_clicked = models.BooleanField(
        default=False,
        help_text='Whether the user clicked/interacted with this recommendation'
    )
    
    class Meta:
        db_table = 'recommendation_log'
        verbose_name = 'Recommendation Log'
        verbose_name_plural = 'Recommendation Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at', 'recommendation_type'], name='rec_log_created_type_idx'),
            models.Index(fields=['customer'], name='rec_log_customer_idx'),
        ]
    
    def __str__(self):
        user_display = self.customer.username if self.customer else 'Anonymous'
        if self.restaurant:
            return f'{user_display} - {self.get_recommendation_type_display()} - {self.restaurant.name}'
        elif self.menu_item:
            return f'{user_display} - {self.get_recommendation_type_display()} - {self.menu_item.name}'
        return f'{user_display} - {self.get_recommendation_type_display()}'
