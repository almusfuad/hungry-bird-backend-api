"""Restaurant order analytics.

Daily order statistics, order source comparison, and order trends.
"""

from datetime import datetime
from typing import Optional

from django.db.models import Count, Sum, Avg, Q, Case, When
from django.db.models.functions import TruncDate

from order.models import Order


def get_daily_orders(restaurant_id, date_start: Optional[datetime] = None, date_end: Optional[datetime] = None, order_source: Optional[int] = None):
    """Get daily order statistics for a restaurant."""
    queryset = Order.objects.filter(restaurant_id=restaurant_id)
    
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    if order_source:
        queryset = queryset.filter(order_source=order_source)
    
    results = queryset.annotate(
        date=TruncDate('created_at')
    ).values('date', 'order_source').annotate(
        total_orders=Count('id'),
        revenue=Sum('total_price'),
        avg_order_value=Avg('total_price'),
        completed=Count(Case(When(Q(status=5) | Q(status=7), then=1))),
        cancelled=Count(Case(When(status=6, then=1))),
        pending=Count(Case(When(status=1, then=1)))
    ).order_by('-date')
    
    return list(results)


def get_order_source_comparison(restaurant_id, date_start: Optional[datetime] = None, date_end: Optional[datetime] = None):
    """Compare POS vs Online orders with payment breakdown."""
    queryset = Order.objects.filter(restaurant_id=restaurant_id)
    
    if date_start:
        queryset = queryset.filter(created_at__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__lte=date_end)
    
    results = queryset.values('order_source').annotate(
        total_orders=Count('id'),
        total_revenue=Sum('total_price'),
        avg_order_value=Avg('total_price'),
        completed=Count(Case(When(Q(status=5) | Q(status=7), then=1))),
        cancelled=Count(Case(When(status=6, then=1))),
        # Payment method breakdown
        cod_payments=Count(Case(When(payment__payment_method=1, then=1))),
        stripe_payments=Count(Case(When(payment__payment_method=2, then=1))),
        cash_payments=Count(Case(When(payment__payment_method=3, then=1))),
        mfs_payments=Count(Case(When(payment__payment_method=4, then=1))),
        card_payments=Count(Case(When(payment__payment_method=5, then=1)))
    ).order_by('order_source')
    
    return list(results)
