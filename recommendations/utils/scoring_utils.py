"""
Scoring utilities for recommendation engine.

This module provides functions to calculate popularity scores and quality metrics
for restaurants and menu items based on order frequency, ratings, and recency.
"""

from datetime import datetime
from decimal import Decimal
import math
from django.utils import timezone


def normalize_score(value, min_val, max_val):
    """
    Normalize a value to a 0-1 range using min-max normalization.
    
    Args:
        value: The value to normalize
        min_val: Minimum value in the range
        max_val: Maximum value in the range
    
    Returns:
        float: Normalized score between 0.0 and 1.0
    
    Example:
        >>> normalize_score(5, 0, 10)
        0.5
        >>> normalize_score(10, 0, 10)
        1.0
        >>> normalize_score(0, 0, 10)
        0.0
    """
    try:
        value = float(value)
        min_val = float(min_val)
        max_val = float(max_val)
        
        # Handle case where min and max are equal (all values are the same)
        if max_val == min_val:
            return 0.0 if value == min_val else 1.0
        
        # Calculate normalized score
        normalized = (value - min_val) / (max_val - min_val)
        
        # Clamp to [0, 1] range
        return max(0.0, min(1.0, normalized))
    except (TypeError, ValueError):
        return 0.0


def calculate_recency_weight(created_at_date, reference_date=None, max_days=30):
    """
    Calculate recency weight using exponential decay function.
    
    Newer items get higher weights, with exponential decay over time.
    Formula: weight = exp(-days_ago / max_days)
    
    Args:
        created_at_date: datetime or date object when the item was created/ordered
        reference_date: datetime to calculate days_ago from (defaults to now)
        max_days: Time constant for exponential decay (default 30 days)
    
    Returns:
        float: Recency weight between 0.0 and 1.0
    
    Example:
        >>> # Item created today
        >>> calculate_recency_weight(timezone.now().date())
        1.0
        >>> # Item created 30 days ago
        >>> from datetime import timedelta
        >>> old_date = (timezone.now() - timedelta(days=30)).date()
        >>> weight = calculate_recency_weight(old_date)
        >>> 0.36 < weight < 0.37  # exp(-30/30) ≈ 0.368
        True
    """
    try:
        # Set reference date to today if not provided
        if reference_date is None:
            reference_date = timezone.now().date()
        
        # Handle datetime objects by extracting date
        if hasattr(created_at_date, 'date'):
            created_at_date = created_at_date.date()
        if hasattr(reference_date, 'date'):
            reference_date = reference_date.date()
        
        # Calculate days ago
        days_ago = (reference_date - created_at_date).days
        
        # Ensure non-negative days
        days_ago = max(0, days_ago)
        
        # Apply exponential decay formula
        weight = math.exp(-days_ago / max_days)
        
        return weight
    except (TypeError, AttributeError):
        return 0.0


def combine_weighted_scores(order_frequency_score, rating_score, recency_score):
    """
    Combine multiple scoring dimensions using weighted average.
    
    Weights:
        - Order frequency: 50% (popularity)
        - Rating/Quality: 30% (user satisfaction)
        - Recency: 20% (freshness/current trends)
    
    Args:
        order_frequency_score: Normalized score [0-1] for order frequency
        rating_score: Normalized score [0-1] for rating (rating / 5.0)
        recency_score: Recency weight [0-1] from calculate_recency_weight()
    
    Returns:
        float: Final weighted score in range 0-100
    
    Example:
        >>> combine_weighted_scores(0.8, 0.9, 1.0)
        86.0
        >>> combine_weighted_scores(1.0, 1.0, 1.0)
        100.0
        >>> combine_weighted_scores(0.0, 0.0, 0.0)
        0.0
    """
    try:
        order_frequency_score = float(order_frequency_score) if order_frequency_score is not None else 0.0
        rating_score = float(rating_score) if rating_score is not None else 0.0
        recency_score = float(recency_score) if recency_score is not None else 0.0
        
        # Apply weights: 50% frequency, 30% rating, 20% recency
        weighted_score = (
            0.5 * order_frequency_score +
            0.3 * rating_score +
            0.2 * recency_score
        )
        
        # Scale to 0-100 range
        final_score = weighted_score * 100.0
        
        return final_score
    except (TypeError, ValueError):
        return 0.0


def calculate_popularity_score(
    order_count,
    total_orders_max,
    average_rating,
    latest_order_date,
    max_days=30
):
    """
    Calculate comprehensive popularity score for a menu item or restaurant.
    
    Combines order frequency, rating quality, and recency into a single score.
    
    Args:
        order_count: Number of times ordered
        total_orders_max: Maximum order count in dataset (for normalization)
        average_rating: Average rating (1.0-5.0 scale)
        latest_order_date: Date of most recent order
        max_days: Time constant for recency decay (default 30 days)
    
    Returns:
        float: Popularity score in range 0-100
    
    Example:
        >>> from datetime import timedelta
        >>> today = timezone.now().date()
        >>> calculate_popularity_score(50, 100, 4.5, today)
        68.0  # (0.5*0.5 + 0.3*0.9 + 0.2*1.0) * 100
    """
    # Normalize order frequency (0-1)
    frequency_score = normalize_score(order_count, 0, total_orders_max)
    
    # Normalize rating (0-1) where 5.0 is perfect
    try:
        average_rating = float(average_rating) if average_rating else 0.0
        rating_score = normalize_score(average_rating, 0, 5.0)
    except (TypeError, ValueError):
        rating_score = 0.0
    
    # Calculate recency weight
    recency_score = calculate_recency_weight(latest_order_date, max_days=max_days)
    
    # Combine all scores
    return combine_weighted_scores(frequency_score, rating_score, recency_score)


def get_discovery_threshold(all_scores):
    """
    Calculate a threshold for 'discovery' recommendations.
    
    Returns a threshold at the 60th percentile of scores to recommend
    items that are good but not yet as popular as top items.
    
    Args:
        all_scores: List of popularity scores
    
    Returns:
        float: Threshold score (60th percentile)
    """
    if not all_scores:
        return 0.0
    
    sorted_scores = sorted(all_scores)
    percentile_index = int(len(sorted_scores) * 0.6)
    return sorted_scores[percentile_index]
