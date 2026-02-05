from dashboard.utils.cache_invalidation import (
    invalidate_on_order_change,
    invalidate_on_payment_change
)
import logging

logger = logging.getLogger(__name__)


class InvalidateOnOrderChangeMixin:
    """
    Mixin for ViewSets that modify Order objects.
    
    Automatically invalidates relevant dashboard caches when orders are
    created, updated, or deleted.
    
    Invalidates caches for:
    - Restaurant: daily_orders, order_source, customer_rankings, driver_performance
    - Customer: customer_overview
    - Driver: driver_overview (if driver assigned)
    
    Usage:
        class OrderViewSet(InvalidateOnOrderChangeMixin, ModelViewSet):
            queryset = Order.objects.all()
            serializer_class = OrderSerializer
    """
    
    def perform_create(self, serializer):
        """Invalidate caches after creating order"""
        order = serializer.save()
        invalidate_on_order_change(order)
        logger.debug(f"Invalidated caches after creating order {order.id}")
    
    def perform_update(self, serializer):
        """Invalidate caches after updating order"""
        order = serializer.save()
        invalidate_on_order_change(order)
        logger.debug(f"Invalidated caches after updating order {order.id}")
    
    def perform_destroy(self, instance):
        """Invalidate caches after deleting order"""
        invalidate_on_order_change(instance)
        instance.delete()
        logger.debug(f"Invalidated caches after deleting order {instance.id}")


class InvalidateOnPaymentChangeMixin:
    """
    Mixin for ViewSets that modify Payment objects.
    
    Automatically invalidates relevant dashboard caches when payments are
    created or updated.
    
    Invalidates caches for:
    - Restaurant: order_source (payment method breakdown)
    
    Usage:
        class PaymentViewSet(InvalidateOnPaymentChangeMixin, ModelViewSet):
            queryset = Payment.objects.all()
            serializer_class = PaymentSerializer
    """
    
    def perform_create(self, serializer):
        """Invalidate caches after creating payment"""
        payment = serializer.save()
        invalidate_on_payment_change(payment)
        logger.debug(f"Invalidated caches after creating payment {payment.id}")
    
    def perform_update(self, serializer):
        """Invalidate caches after updating payment"""
        payment = serializer.save()
        invalidate_on_payment_change(payment)
        logger.debug(f"Invalidated caches after updating payment {payment.id}")


class InvalidateOnOrderItemChangeMixin:
    """
    Mixin for ViewSets that modify OrderItem objects.
    
    Automatically invalidates relevant dashboard caches when order items are
    created, updated, or deleted.
    
    Invalidates caches for:
    - Restaurant: popular_items (menu item ordering data)
    
    Usage:
        class OrderItemViewSet(InvalidateOnOrderItemChangeMixin, ModelViewSet):
            queryset = OrderItem.objects.all()
            serializer_class = OrderItemSerializer
    """
    
    def perform_create(self, serializer):
        """Invalidate caches after creating order item"""
        order_item = serializer.save()
        from dashboard.utils.cache_invalidation import invalidate_on_order_item_change
        invalidate_on_order_item_change(order_item)
        logger.debug(f"Invalidated caches after creating order item {order_item.id}")
    
    def perform_update(self, serializer):
        """Invalidate caches after updating order item"""
        order_item = serializer.save()
        from dashboard.utils.cache_invalidation import invalidate_on_order_item_change
        invalidate_on_order_item_change(order_item)
        logger.debug(f"Invalidated caches after updating order item {order_item.id}")
    
    def perform_destroy(self, instance):
        """Invalidate caches after deleting order item"""
        from dashboard.utils.cache_invalidation import invalidate_on_order_item_change
        invalidate_on_order_item_change(instance)
        instance.delete()
        logger.debug(f"Invalidated caches after deleting order item {instance.id}")
