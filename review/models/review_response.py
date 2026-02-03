from django.db import models
from django.core.exceptions import ValidationError


class ReviewResponse(models.Model):
    """
    Model to store restaurant owner responses to customer reviews.
    Each review can have only one response (OneToOne relationship).
    Responses are immutable once created.
    """
    review = models.OneToOneField(
        'review.Review',
        on_delete=models.CASCADE,
        related_name='response'
    )
    owner = models.ForeignKey(
        'authUser.User',
        on_delete=models.DO_NOTHING,
        related_name='review_responses',
        limit_choices_to={'role': 2}
    )
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Response by {self.owner.username} to review #{self.review.id}"

    def get_display_name(self):
        """
        Get the display name for the responder.
        Returns the restaurant name instead of owner's username.
        """
        return self.review.restaurant.name

    def clean(self):
        """
        Validate that the owner responding is the owner of the restaurant being reviewed.
        """
        if self.review.restaurant.owner != self.owner:
            raise ValidationError({
                'owner': 'Only the restaurant owner can respond to reviews for their restaurant.'
            })

    def save(self, *args, **kwargs):
        """
        Override save to call full_clean for model-level validation.
        """
        self.full_clean()
        super().save(*args, **kwargs)
