"""
Management command to seed recommendation logs for testing and demo purposes.

Creates sample recommendation logs with realistic patterns:
- 40% nearby restaurant recommendations
- 40% popular item recommendations
- 20% personalized recommendations

Logs are created for existing customers with timestamps spread over the past 30 days.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from authUser.models import User
from restaurant.models import Restaurant, MenuItem
from recommendations.models import RecommendationLog
from hungryBird.utils import calculate_distance


class Command(BaseCommand):
    help = 'Seed recommendation logs for testing and demo purposes'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--count',
            type=int,
            default=75,
            help='Number of recommendation logs to create (default: 75)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing recommendation logs before seeding'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        count = options['count']
        clear = options['clear']
        
        # Clear existing logs if requested
        if clear:
            self.stdout.write(self.style.WARNING('Clearing existing recommendation logs...'))
            deleted_count, _ = RecommendationLog.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {deleted_count} existing logs'))
        
        # Check if we have required data
        customers = User.objects.filter(role=1)  # Customers only
        restaurants = Restaurant.objects.filter(is_active=True)
        menu_items = MenuItem.objects.filter(is_active=True)
        
        if not customers.exists():
            raise CommandError('No customers found in the database. Please create some users first.')
        
        if not restaurants.exists():
            raise CommandError('No restaurants found in the database. Please create some restaurants first.')
        
        if not menu_items.exists():
            raise CommandError('No menu items found in the database. Please create some menu items first.')
        
        self.stdout.write(self.style.SUCCESS(f'Found {customers.count()} customers'))
        self.stdout.write(self.style.SUCCESS(f'Found {restaurants.count()} restaurants'))
        self.stdout.write(self.style.SUCCESS(f'Found {menu_items.count()} menu items'))
        
        # Create recommendation logs
        self.stdout.write(f'\nCreating {count} recommendation logs...')
        
        logs_created = 0
        logs = []
        
        for i in range(count):
            # Randomly select recommendation type (40% nearby, 40% popular, 20% personalized)
            rand = random.random()
            if rand < 0.4:
                rec_type = RecommendationLog.NEARBY_RESTAURANT
            elif rand < 0.8:
                rec_type = RecommendationLog.POPULAR_ITEM
            else:
                rec_type = RecommendationLog.PERSONALIZED
            
            # Select random customer (80% authenticated, 20% anonymous)
            customer = None
            if random.random() < 0.8:
                customer = customers.order_by('?').first()
            
            # Get random restaurant
            restaurant = restaurants.order_by('?').first()
            
            # Generate location near the restaurant (within 10km)
            base_lat = float(restaurant.latitude)
            base_lon = float(restaurant.longitude)
            
            # Add random offset (approximately 0-10km)
            lat_offset = random.uniform(-0.08, 0.08)
            lon_offset = random.uniform(-0.08, 0.08)
            user_lat = Decimal(str(base_lat + lat_offset))
            user_lon = Decimal(str(base_lon + lon_offset))
            
            # Get search radius
            search_radius = Decimal(str(random.uniform(5.0, 15.0)))
            
            # Select menu item if this is a popular item or personalized recommendation
            menu_item = None
            if rec_type in [RecommendationLog.POPULAR_ITEM, RecommendationLog.PERSONALIZED]:
                # Try to get item from the same restaurant for consistency
                restaurant_items = menu_items.filter(restaurant=restaurant)
                if restaurant_items.exists():
                    menu_item = restaurant_items.order_by('?').first()
                else:
                    menu_item = menu_items.order_by('?').first()
            
            # Generate random timestamp within past 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            timestamp = timezone.now() - timedelta(
                days=days_ago,
                hours=hours_ago,
                minutes=minutes_ago
            )
            
            # 20% chance of being clicked
            was_clicked = random.random() < 0.2
            
            # Create log entry
            log = RecommendationLog(
                customer=customer,
                recommendation_type=rec_type,
                restaurant=restaurant if rec_type == RecommendationLog.NEARBY_RESTAURANT else None,
                menu_item=menu_item,
                user_latitude=user_lat,
                user_longitude=user_lon,
                search_radius=search_radius,
                was_clicked=was_clicked,
                created_at=timestamp,
                updated_at=timestamp,
            )
            
            logs.append(log)
        
        # Bulk create all logs
        RecommendationLog.objects.bulk_create(logs, batch_size=100)
        logs_created = len(logs)
        
        # Display results
        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully created {logs_created} recommendation logs\n'))
        
        # Show statistics
        nearby_count = RecommendationLog.objects.filter(
            recommendation_type=RecommendationLog.NEARBY_RESTAURANT
        ).count()
        popular_count = RecommendationLog.objects.filter(
            recommendation_type=RecommendationLog.POPULAR_ITEM
        ).count()
        personalized_count = RecommendationLog.objects.filter(
            recommendation_type=RecommendationLog.PERSONALIZED
        ).count()
        clicked_count = RecommendationLog.objects.filter(was_clicked=True).count()
        anonymous_count = RecommendationLog.objects.filter(customer__isnull=True).count()
        
        self.stdout.write('Statistics:')
        self.stdout.write(f'  • Nearby Restaurant: {nearby_count} ({nearby_count*100//logs_created}%)')
        self.stdout.write(f'  • Popular Items: {popular_count} ({popular_count*100//logs_created}%)')
        self.stdout.write(f'  • Personalized: {personalized_count} ({personalized_count*100//logs_created}%)')
        self.stdout.write(f'  • Clicked: {clicked_count} ({clicked_count*100//logs_created}%)')
        self.stdout.write(f'  • Anonymous: {anonymous_count} ({anonymous_count*100//logs_created}%)')
        self.stdout.write(f'  • Authenticated: {logs_created - anonymous_count} ({(logs_created-anonymous_count)*100//logs_created}%)')
