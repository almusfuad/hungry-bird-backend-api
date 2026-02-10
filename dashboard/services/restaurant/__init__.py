"""Restaurant dashboard service package.

Modular services for restaurant owner analytics and metrics.
"""

from .orders import get_daily_orders, get_order_source_comparison
from .customers import get_top_customers, get_customer_retention_metrics
from .items import get_popular_items, get_peak_hours_analysis
from .performance import get_driver_performance, get_period_comparison

__all__ = [
    'get_daily_orders',
    'get_order_source_comparison',
    'get_top_customers',
    'get_customer_retention_metrics',
    'get_popular_items',
    'get_peak_hours_analysis',
    'get_driver_performance',
    'get_period_comparison',
]
