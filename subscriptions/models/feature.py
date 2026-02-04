from django.db import models
from django.core.exceptions import ValidationError
from hungryBird.baseModels import TimeStampedModel
import re


class Feature(TimeStampedModel):
    """
    Features that can be included in subscription plans.
    Each feature maps to specific API endpoints/functionalities.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Feature name (e.g., food_ordering, pos_ordering, analytics)"
    )
    description = models.TextField(
        help_text="Description of what this feature provides"
    )
    url_patterns = models.TextField(
        help_text="URL patterns for this feature (one per line). Use glob patterns like restaurant/*, order/create"
    )

    class Meta:
        db_table = 'subscription_features'
        ordering = ['name']
        verbose_name = 'Feature'
        verbose_name_plural = 'Features'

    def __str__(self):
        return self.name

    def clean(self):
        """
        Validate that all URL patterns are valid glob patterns.
        Patterns should only contain alphanumeric characters, underscores, slashes, hyphens, and wildcards.
        """
        super().clean()
        
        if self.url_patterns:
            lines = self.url_patterns.strip().split('\n')
            invalid_patterns = []
            
            for line in lines:
                pattern = line.strip()
                if not pattern:  # Skip empty lines
                    continue
                
                # Validate pattern: alphanumeric, underscore, slash, hyphen, asterisk only
                if not re.match(r'^[a-zA-Z0-9_/*-]+$', pattern):
                    invalid_patterns.append(pattern)
            
            if invalid_patterns:
                raise ValidationError({
                    'url_patterns': f"Invalid URL patterns: {', '.join(invalid_patterns)}. "
                                   "Patterns should only contain letters, numbers, underscores, slashes, hyphens, and asterisks."
                })

    def get_patterns_list(self):
        """
        Get URL patterns as a list of strings.
        
        Returns:
            list: List of URL pattern strings
        """
        if not self.url_patterns:
            return []
        
        patterns = []
        for line in self.url_patterns.strip().split('\n'):
            pattern = line.strip()
            if pattern:
                patterns.append(pattern)
        return patterns
