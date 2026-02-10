"""Platform dashboard service package.

Modular services for platform-wide analytics and statistics.
"""

from .revenue import get_platform_revenue_stats
from .trends import get_order_trends
from .rankings import get_trending_items, get_top_restaurants, get_customer_metrics

__all__ = [
    'get_platform_revenue_stats',
    'get_order_trends',
    'get_trending_items',
    'get_top_restaurants',
    'get_customer_metrics',
]
