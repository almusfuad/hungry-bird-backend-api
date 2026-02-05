from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from order.models import Order
from dashboard.models import OrderStatusTransition


class Command(BaseCommand):
    help = 'Backfill OrderStatusTransition for existing orders'
    
    def handle(self, *args, **options):
        self.stdout.write('Starting backfill...')
        
        orders = Order.objects.filter(statustransitions__isnull=True)
        count = 0
        
        for order in orders:
            transitions = []
            time_span = (order.updated_at - order.created_at).total_seconds()
            
            # Generate transitions based on status
            if order.order_source == 1:  # Online
                if order.status == 5:
                    statuses = [1, 2, 3, 4, 5]
                elif order.status == 6:
                    statuses = [1, 2, 6]
                elif order.status >= 1:
                    statuses = list(range(1, order.status + 1))
                else:
                    statuses = [1]
            else:  # POS
                if order.status == 7:
                    statuses = [1, 2, 7]
                elif order.status == 6:
                    statuses = [1, 2, 6]
                else:
                    statuses = [1, 2]
            
            time_step = time_span / max(len(statuses) - 1, 1)
            
            for i in range(len(statuses) - 1):
                transitions.append(OrderStatusTransition(
                    order=order,
                    from_status=statuses[i],
                    to_status=statuses[i + 1],
                    transitioned_at=order.created_at + timedelta(seconds=time_step * (i + 1)),
                    is_backfilled=True
                ))
            
            if transitions:
                OrderStatusTransition.objects.bulk_create(transitions)
                count += len(transitions)
        
        self.stdout.write(self.style.SUCCESS(f'Created {count} transitions for {orders.count()} orders'))
