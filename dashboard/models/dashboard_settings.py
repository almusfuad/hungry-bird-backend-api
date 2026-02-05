import os

"""
Dashboard configuration settings loaded from environment variables.

These settings control caching behavior, polling intervals, and cache warming
strategies for the dashboard analytics system.
"""

# Polling intervals in seconds for different user roles
# Determines how frequently frontend should poll for updated dashboard data
POLLING_INTERVALS = {
    'RESTAURANT': 300,   # 5 minutes for restaurant owners
    'CUSTOMER': 900,     # 15 minutes for customers  
    'DRIVER': 600,       # 10 minutes for drivers
}

# Metrics to pre-warm in cache for active entities
# Only these metrics will be pre-computed by Celery tasks to optimize performance
CACHE_WARM_METRICS = [
    'daily_orders',         # Restaurant daily order statistics
    'popular_items',        # Most ordered menu items
    'driver_performance',   # Driver delivery performance metrics
]

# Cache only stores data for last N days
# Queries outside this range will bypass cache and query database directly
CACHE_DAYS_LIMIT = 7

# Threshold for defining "active" entities eligible for cache warming
# Entities (restaurants/customers/drivers) with orders in last N days
DASHBOARD_ACTIVE_THRESHOLD_DAYS = int(os.getenv('DASHBOARD_ACTIVE_THRESHOLD_DAYS', '7'))
