from django.db import models
from hungryBird.baseModels import TimeStampedModel


class HelpfulVote(TimeStampedModel):
    """
    Model to store helpful votes on reviews.
    Customers can vote if a review is helpful or not.
    One user can vote only once per review (unique_together constraint).
    """
    review = models.ForeignKey(
        'review.Review',
        on_delete=models.CASCADE,
        related_name='helpful_votes'
    )
    user = models.ForeignKey(
        'authUser.User',
        on_delete=models.CASCADE,
        related_name='helpful_votes_given'
    )
    is_helpful = models.BooleanField(default=True)

    class Meta:
        unique_together = [('review', 'user')]
        ordering = ['-created_at']

    def __str__(self):
        vote_type = "helpful" if self.is_helpful else "not helpful"
        return f"{self.user.username} voted {vote_type} on review #{self.review.id}"
