"""Serializers for forecasting and advanced analytics endpoints.

This module provides request validation and response formatting
for forecasting, trend analysis, and comparative metrics.
"""

from rest_framework import serializers


class ForecastRequestSerializer(serializers.Serializer):
    """Serializer for revenue forecast requests."""
    
    periods_ahead = serializers.IntegerField(
        default=7,
        min_value=1,
        max_value=90,
        help_text="Number of days to forecast ahead (1-90)"
    )
    method = serializers.ChoiceField(
        choices=['moving_average', 'exponential_smoothing', 'linear_trend'],
        default='moving_average',
        help_text="Forecasting method to use"
    )
    date_start = serializers.DateField(
        required=False,
        help_text="Start date for historical data"
    )
    date_end = serializers.DateField(
        required=False,
        help_text="End date for historical data"
    )


class GrowthRateRequestSerializer(serializers.Serializer):
    """Serializer for growth rate comparison requests."""
    
    comparison_type = serializers.ChoiceField(
        choices=['mom', 'wow', 'yoy'],
        default='mom',
        help_text="Comparison type: mom (month-over-month), wow (week-over-week), yoy (year-over-year)"
    )
    current_period_start = serializers.DateField(
        required=False,
        help_text="Start of current period"
    )
    current_period_end = serializers.DateField(
        required=False,
        help_text="End of current period"
    )


class DemandPatternsRequestSerializer(serializers.Serializer):
    """Serializer for demand pattern analysis requests."""
    
    analysis_days = serializers.IntegerField(
        default=30,
        min_value=7,
        max_value=365,
        help_text="Number of days of historical data to analyze (7-365)"
    )


class TrendRequestSerializer(serializers.Serializer):
    """Serializer for order trend requests."""
    
    grouping = serializers.ChoiceField(
        choices=['hourly', 'daily', 'weekly', 'monthly'],
        default='daily',
        help_text="Time grouping for trend data"
    )
    date_start = serializers.DateField(
        required=False,
        help_text="Start date for filtering"
    )
    date_end = serializers.DateField(
        required=False,
        help_text="End date for filtering"
    )
    limit = serializers.IntegerField(
        default=30,
        min_value=1,
        max_value=365,
        help_text="Maximum number of periods to return"
    )


class PaginationSerializer(serializers.Serializer):
    """Serializer for pagination parameters."""
    
    page = serializers.IntegerField(
        default=1,
        min_value=1,
        help_text="Page number"
    )
    page_size = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100,
        help_text="Number of items per page (max 100)"
    )


class DriverPerformanceRequestSerializer(serializers.Serializer):
    """Serializer for driver performance requests."""
    
    date_start = serializers.DateField(
        required=False,
        help_text="Start date for filtering"
    )
    date_end = serializers.DateField(
        required=False,
        help_text="End date for filtering"
    )
    grouping = serializers.ChoiceField(
        choices=['daily', 'weekly', 'monthly'],
        default='weekly',
        help_text="Time grouping for performance history"
    )
    limit = serializers.IntegerField(
        default=12,
        min_value=1,
        max_value=52,
        help_text="Maximum number of periods to return"
    )


class PlatformStatsRequestSerializer(serializers.Serializer):
    """Serializer for platform-wide statistics requests."""
    
    date_start = serializers.DateField(
        required=False,
        help_text="Start date for filtering"
    )
    date_end = serializers.DateField(
        required=False,
        help_text="End date for filtering"
    )
    order_source = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=2,
        help_text="Filter by order source (1=Online, 2=POS)"
    )


class TopItemsRequestSerializer(serializers.Serializer):
    """Serializer for trending/top items requests."""
    
    date_start = serializers.DateField(
        required=False,
        help_text="Start date for filtering"
    )
    date_end = serializers.DateField(
        required=False,
        help_text="End date for filtering"
    )
    limit = serializers.IntegerField(
        default=50,
        min_value=1,
        max_value=100,
        help_text="Maximum number of items to return"
    )


class RestaurantRankingRequestSerializer(serializers.Serializer):
    """Serializer for restaurant ranking requests."""
    
    date_start = serializers.DateField(
        required=False,
        help_text="Start date for filtering"
    )
    date_end = serializers.DateField(
        required=False,
        help_text="End date for filtering"
    )
    limit = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100,
        help_text="Maximum number of restaurants to return"
    )


class DriverRankingRequestSerializer(serializers.Serializer):
    """Serializer for driver ranking requests."""
    
    restaurant_id = serializers.IntegerField(
        required=False,
        help_text="Filter by restaurant ID"
    )
    date_start = serializers.DateField(
        required=False,
        help_text="Start date for filtering"
    )
    date_end = serializers.DateField(
        required=False,
        help_text="End date for filtering"
    )
    limit = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100,
        help_text="Maximum number of drivers to return"
    )
