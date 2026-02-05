from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from order.models import Order
from dashboard.models import OrderStatusTransition
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to backfill OrderStatusTransition records for existing orders.
    
    This is a one-time command that runs after deployment to create historical
    status transitions for orders that existed before the dashboard app was added.
    
    The command estimates status transitions based on order source and status:
    
    Online Orders (order_source=1):
    - If order_status=5 (Delivered): Estimates 1→2→3→4→5 transitions
    - If order_status=6 (Cancelled): Estimates partial transitions up to cancel point
    - If order_status=1-4: Estimates partial transitions up to current status
    
    POS Orders (order_source=2):
    - If order_status=7 (Completed): Creates 1→2→7 transitions
    - If order_status=6 (Cancelled): Creates 1→2→6 transitions
    - If order_status=1-2: Creates partial transitions
    
    Status codes:
    1=Pending, 2=Preparing, 3=Ready for Pickup, 4=Out for Delivery, 
    5=Delivered, 6=Cancelled, 7=Completed (POS only)
    
    All backfilled transitions are marked with is_backfilled=True for identification.
    """
    
    help = 'Backfill OrderStatusTransition records for existing orders (one-time post-deployment command)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without saving to database, just show what would be created'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of orders to process per batch (default: 1000)'
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        batch_size = options.get('batch_size', 1000)
        
        self.stdout.write(self.style.SUCCESS('\n=== Dashboard OrderStatusTransition Backfill ===\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN MODE - No data will be saved'))
        
        # Get all orders that don't already have status transitions
        total_orders = Order.objects.count()
        orders_with_transitions = OrderStatusTransition.objects.values_list('order_id', flat=True).distinct().count()
        orders_needing_backfill = total_orders - orders_with_transitions
        
        self.stdout.write(f'Total orders: {total_orders}')
        self.stdout.write(f'Orders with transitions: {orders_with_transitions}')
        self.stdout.write(f'Orders needing backfill: {orders_needing_backfill}\n')
        
        if orders_needing_backfill == 0:
            self.stdout.write(self.style.SUCCESS('✓ All orders already have status transitions. No backfill needed.'))
            return
        
        # Get orders without transitions
        orders_to_backfill = Order.objects.filter(
            statustransitions__isnull=True
        ).select_related('restaurant', 'customer', 'driver')
        
        total_created = 0
        errors = 0
        
        # Process in batches
        for offset in range(0, orders_needing_backfill, batch_size):
            batch = orders_to_backfill[offset:offset + batch_size]
            batch_transitions = []
            
            for order in batch:
                try:
                    transitions = self._generate_transitions(order)
                    batch_transitions.extend(transitions)
                except Exception as e:
                    logger.error(f"Error processing order {order.id}: {str(e)}")
                    errors += 1
                    continue
            
            # Bulk create transitions
            if not dry_run and batch_transitions:
                try:
                    OrderStatusTransition.objects.bulk_create(batch_transitions, batch_size=500)
                    self.stdout.write(f'✓ Batch {offset // batch_size + 1}: Created {len(batch_transitions)} transitions')
                    total_created += len(batch_transitions)
                except Exception as e:
                    logger.error(f"Error bulk creating transitions: {str(e)}")
                    errors += 1
            elif dry_run and batch_transitions:
                self.stdout.write(f'[DRY RUN] Batch {offset // batch_size + 1}: Would create {len(batch_transitions)} transitions')
                total_created += len(batch_transitions)
        
        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'✓ Backfill Complete!'))
        self.stdout.write(f'Total transitions created: {total_created}')
        self.stdout.write(f'Errors: {errors}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No data was actually saved. Run without --dry-run to perform actual backfill.'))
        else:
            self.stdout.write(self.style.SUCCESS('\nAll historical status transitions have been backfilled.'))
    
    def _generate_transitions(self, order):
        """
        Generate estimated status transitions for an order based on its current state.
        
        Returns list of OrderStatusTransition objects (not yet saved).
        """
        transitions = []
        
        # Estimate timing: spread transitions evenly over order's time span
        time_span = (order.updated_at - order.created_at).total_seconds()
        
        if order.order_source == 1:  # Online order
            transitions = self._generate_online_transitions(order, time_span)
        elif order.order_source == 2:  # POS order
            transitions = self._generate_pos_transitions(order, time_span)
        
        return transitions
    
    def _generate_online_transitions(self, order, time_span):
        """Generate transitions for online orders (source=1)"""
        transitions = []
        
        # Online status progression: 1→2→3→4→5 (or stops at current status / 6=Cancelled)
        status_sequence = []
        
        if order.status == 5:  # Delivered
            status_sequence = [1, 2, 3, 4, 5]
        elif order.status == 6:  # Cancelled
            status_sequence = [1, 2, 6]  # Assume cancelled after preparing
        elif order.status == 4:  # Out for Delivery
            status_sequence = [1, 2, 3, 4]
        elif order.status == 3:  # Ready for Pickup
            status_sequence = [1, 2, 3]
        elif order.status == 2:  # Preparing
            status_sequence = [1, 2]
        else:  # Pending or unknown
            status_sequence = [1]
        
        # Create transitions with estimated timestamps
        num_transitions = len(status_sequence)
        time_step = time_span / max(num_transitions, 1)
        
        for i in range(len(status_sequence) - 1):
            from_status = status_sequence[i]
            to_status = status_sequence[i + 1]
            transitioned_at = order.created_at + timedelta(seconds=time_step * (i + 1))
            
            transitions.append(
                OrderStatusTransition(
                    order=order,
                    from_status=from_status,
                    to_status=to_status,
                    transitioned_at=transitioned_at,
                    driver_location_lat=None,
                    driver_location_lon=None,
                    is_backfilled=True
                )
            )
        
        return transitions
    
    def _generate_pos_transitions(self, order, time_span):
        """Generate transitions for POS orders (source=2)"""
        transitions = []
        
        # POS status progression: 1→2→7 (Completed) or 1→2→6 (Cancelled)
        status_sequence = []
        
        if order.status == 7:  # Completed
            status_sequence = [1, 2, 7]
        elif order.status == 6:  # Cancelled
            status_sequence = [1, 2, 6]
        elif order.status == 2:  # Preparing
            status_sequence = [1, 2]
        else:  # Pending
            status_sequence = [1]
        
        # Create transitions with estimated timestamps
        num_transitions = len(status_sequence)
        time_step = time_span / max(num_transitions, 1)
        
        for i in range(len(status_sequence) - 1):
            from_status = status_sequence[i]
            to_status = status_sequence[i + 1]
            transitioned_at = order.created_at + timedelta(seconds=time_step * (i + 1))
            
            transitions.append(
                OrderStatusTransition(
                    order=order,
                    from_status=from_status,
                    to_status=to_status,
                    transitioned_at=transitioned_at,
                    driver_location_lat=None,
                    driver_location_lon=None,
                    is_backfilled=True
                )
            )
        
        return transitions
