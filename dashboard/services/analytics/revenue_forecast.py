"""Revenue forecasting analytics.

Statistical forecasting methods for revenue prediction.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from django.core.cache import cache
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from order.models import Order


def forecast_revenue(
    restaurant_id: Optional[int] = None,
    periods_ahead: int = 7,
    method: str = 'moving_average',
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None
) -> Dict[str, Any]:
    """Forecast future revenue using simple statistical methods.
    
    Args:
        restaurant_id: Restaurant ID for restaurant-specific forecast.
                      If None, forecasts platform-wide revenue.
        periods_ahead: Number of days to forecast ahead.
        method: Forecasting method - 'moving_average', 'exponential_smoothing',
                or 'linear_trend'.
        date_start: Start date for historical data (inclusive).
        date_end: End date for historical data (inclusive).
        
    Returns:
        Dictionary containing historical data, forecast values,
        and forecast metadata.
    """
    cache_key = f"forecast_revenue_{restaurant_id}_{periods_ahead}_{method}_{date_start}_{date_end}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data
    
    # Get historical daily revenue
    queryset = Order.objects.filter(is_active=True, status__in=[5, 7])
    
    if restaurant_id:
        queryset = queryset.filter(restaurant_id=restaurant_id)
    
    if not date_end:
        date_end = timezone.now()
    if not date_start:
        date_start = date_end - timedelta(days=30)
    
    queryset = queryset.filter(created_at__gte=date_start, created_at__lte=date_end)
    
    # Get daily revenue history
    historical_data = queryset.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        revenue=Sum('total_price'),
        order_count=Count('id')
    ).order_by('date')
    
    # Convert to list for processing
    history = [
        {
            'date': item['date'].isoformat(),
            'revenue': float(item['revenue'] or 0),
            'order_count': item['order_count']
        }
        for item in historical_data
    ]
    
    if not history:
        return {
            'historical_data': [],
            'forecast': [],
            'method': method,
            'periods_ahead': periods_ahead,
            'message': 'Insufficient historical data for forecasting'
        }
    
    # Extract revenue values
    revenue_values = [item['revenue'] for item in history]
    
    # Generate forecast based on method
    if method == 'moving_average':
        forecast_values = _moving_average_forecast(revenue_values, periods_ahead, window=7)
    elif method == 'exponential_smoothing':
        forecast_values = _exponential_smoothing_forecast(revenue_values, periods_ahead, alpha=0.3)
    elif method == 'linear_trend':
        forecast_values = _linear_trend_forecast(revenue_values, periods_ahead)
    else:
        forecast_values = _moving_average_forecast(revenue_values, periods_ahead)
    
    # Generate forecast dates
    last_date = datetime.fromisoformat(history[-1]['date'])
    forecast = []
    for i in range(1, periods_ahead + 1):
        forecast_date = last_date + timedelta(days=i)
        forecast.append({
            'date': forecast_date.isoformat(),
            'forecasted_revenue': round(forecast_values[i - 1], 2),
            'confidence': 'medium'  # Placeholder for confidence interval
        })
    
    result = {
        'historical_data': history,
        'forecast': forecast,
        'method': method,
        'periods_ahead': periods_ahead,
        'avg_historical_revenue': round(sum(revenue_values) / len(revenue_values), 2),
        'total_historical_revenue': round(sum(revenue_values), 2),
    }
    
    # Cache for 30 minutes
    cache.set(cache_key, result, 1800)
    
    return result


def _moving_average_forecast(
    values: List[float],
    periods: int,
    window: int = 7
) -> List[float]:
    """Simple moving average forecast.
    
    Args:
        values: Historical values.
        periods: Number of periods to forecast.
        window: Moving average window size.
        
    Returns:
        List of forecasted values.
    """
    if len(values) < window:
        window = len(values)
    
    # Calculate moving average of last 'window' periods
    moving_avg = sum(values[-window:]) / window
    
    # Forecast all periods with the same moving average
    return [moving_avg] * periods


def _exponential_smoothing_forecast(
    values: List[float],
    periods: int,
    alpha: float = 0.3
) -> List[float]:
    """Exponential smoothing forecast.
    
    Args:
        values: Historical values.
        periods: Number of periods to forecast.
        alpha: Smoothing factor (0 < alpha < 1).
        
    Returns:
        List of forecasted values.
    """
    if not values:
        return [0] * periods
    
    # Initialize with first value
    smoothed = values[0]
    
    # Apply exponential smoothing to historical data
    for value in values[1:]:
        smoothed = alpha * value + (1 - alpha) * smoothed
    
    # Forecast all periods with last smoothed value
    return [smoothed] * periods


def _linear_trend_forecast(
    values: List[float],
    periods: int
) -> List[float]:
    """Linear trend forecast using simple linear regression.
    
    Args:
        values: Historical values.
        periods: Number of periods to forecast.
        
    Returns:
        List of forecasted values.
    """
    n = len(values)
    if n < 2:
        return [values[0] if values else 0] * periods
    
    # Calculate slope and intercept using least squares
    x_values = list(range(n))
    x_mean = sum(x_values) / n
    y_mean = sum(values) / n
    
    numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    
    if denominator == 0:
        return [y_mean] * periods
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Forecast future values
    forecast = []
    for i in range(n, n + periods):
        forecast.append(max(0, slope * i + intercept))  # Ensure non-negative
    
    return forecast
