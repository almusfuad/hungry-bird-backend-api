"""Analytics service package.

Statistical forecasting and predictive analytics modules.
"""

from .revenue_forecast import forecast_revenue
from .growth import calculate_growth_rate
from .demand import predict_demand_patterns

__all__ = [
    'forecast_revenue',
    'calculate_growth_rate',
    'predict_demand_patterns',
]
