from django.core.management.base import BaseCommand
from django.db import transaction
from subscriptions.models import SubscriptionPlan, Feature, PlanFeature


class Command(BaseCommand):
    help = 'Seed initial subscription plans and features'

    def handle(self, *args, **kwargs):
        """
        Create initial subscription plans and features.
        This command is idempotent - can be run multiple times safely.
        """
        self.stdout.write(self.style.SUCCESS('Starting subscription plans and features seeding...'))
        
        try:
            with transaction.atomic():
                # Create Features
                self.stdout.write('Creating features...')
                
                features_data = [
                    {
                        'name': 'food_ordering',
                        'description': 'Basic food ordering functionality for customers',
                        'url_patterns': 'restaurant/*\norder/create\norder/list\nmenu/*'
                    },
                    {
                        'name': 'pos_ordering',
                        'description': 'Point of Sale ordering system for in-restaurant orders',
                        'url_patterns': 'pos/*\norder/pos/*'
                    },
                    {
                        'name': 'analytics',
                        'description': 'Basic analytics and reporting dashboard',
                        'url_patterns': 'analytics/*\nreports/basic/*'
                    },
                    {
                        'name': 'recommendation_pipeline',
                        'description': 'AI-powered recommendation engine for customers',
                        'url_patterns': 'recommendations/*\nml/*'
                    },
                    {
                        'name': 'advanced_reports',
                        'description': 'Advanced reporting with custom filters and exports',
                        'url_patterns': 'reports/advanced/*\nreports/export/*\nreports/custom/*'
                    },
                    {
                        'name': 'review_management',
                        'description': 'Customer review and rating management',
                        'url_patterns': 'review/*\nratings/*'
                    },
                    {
                        'name': 'driver_management',
                        'description': 'Delivery driver assignment and tracking',
                        'url_patterns': 'driver/*\ndelivery/*'
                    },
                ]
                
                created_features = []
                for feature_data in features_data:
                    feature, created = Feature.objects.get_or_create(
                        name=feature_data['name'],
                        defaults={
                            'description': feature_data['description'],
                            'url_patterns': feature_data['url_patterns'],
                            'is_active': True
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Created feature: {feature.name}'))
                    else:
                        self.stdout.write(f'  - Feature already exists: {feature.name}')
                    created_features.append(feature)
                
                # Create Subscription Plans
                self.stdout.write('\nCreating subscription plans...')
                
                # Free Plan
                free_plan, created = SubscriptionPlan.objects.get_or_create(
                    name='Free',
                    defaults={
                        'stripe_price_id': None,
                        'price': 0.00,
                        'duration_days': 30,
                        'grace_period_days': 3,
                        'description': 'Free plan with basic features for getting started. '
                                     'Includes food ordering, review management, and driver management.',
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created plan: {free_plan.name}'))
                else:
                    self.stdout.write(f'  - Plan already exists: {free_plan.name}')
                
                # Regular Plan
                regular_plan, created = SubscriptionPlan.objects.get_or_create(
                    name='Regular',
                    defaults={
                        'stripe_price_id': None,  # Set this in admin after creating Stripe price
                        'price': 29.99,
                        'duration_days': 30,
                        'grace_period_days': 3,
                        'description': 'Regular plan with POS ordering and basic analytics. '
                                     'Perfect for small to medium restaurants.',
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created plan: {regular_plan.name}'))
                else:
                    self.stdout.write(f'  - Plan already exists: {regular_plan.name}')
                
                # Custom Plan
                custom_plan, created = SubscriptionPlan.objects.get_or_create(
                    name='Custom',
                    defaults={
                        'stripe_price_id': None,  # Set this in admin after creating Stripe price
                        'price': 99.99,
                        'duration_days': 30,
                        'grace_period_days': 3,
                        'description': 'Custom plan with all features and per-user customization. '
                                     'Includes recommendation engine, advanced reports, and full analytics.',
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created plan: {custom_plan.name}'))
                else:
                    self.stdout.write(f'  - Plan already exists: {custom_plan.name}')
                
                # Assign Features to Plans
                self.stdout.write('\nAssigning features to plans...')
                
                # Free Plan Features
                free_features = ['food_ordering', 'review_management', 'driver_management']
                for feature_name in free_features:
                    feature = Feature.objects.get(name=feature_name)
                    plan_feature, created = PlanFeature.objects.get_or_create(
                        plan=free_plan,
                        feature=feature,
                        defaults={'is_enabled': True}
                    )
                    if created:
                        self.stdout.write(f'  ✓ Assigned {feature_name} to Free plan')
                
                # Regular Plan Features (Free + POS + Analytics)
                regular_features = [
                    'food_ordering', 'review_management', 'driver_management',
                    'pos_ordering', 'analytics'
                ]
                for feature_name in regular_features:
                    feature = Feature.objects.get(name=feature_name)
                    plan_feature, created = PlanFeature.objects.get_or_create(
                        plan=regular_plan,
                        feature=feature,
                        defaults={'is_enabled': True}
                    )
                    if created:
                        self.stdout.write(f'  ✓ Assigned {feature_name} to Regular plan')
                
                # Custom Plan Features (All features)
                custom_features = [
                    'food_ordering', 'review_management', 'driver_management',
                    'pos_ordering', 'analytics', 'recommendation_pipeline', 'advanced_reports'
                ]
                for feature_name in custom_features:
                    feature = Feature.objects.get(name=feature_name)
                    plan_feature, created = PlanFeature.objects.get_or_create(
                        plan=custom_plan,
                        feature=feature,
                        defaults={'is_enabled': True}
                    )
                    if created:
                        self.stdout.write(f'  ✓ Assigned {feature_name} to Custom plan')
                
                self.stdout.write('\n' + '='*50)
                self.stdout.write(self.style.SUCCESS('✓ Subscription plans and features seeded successfully!'))
                self.stdout.write('='*50)
                
                # Display summary
                self.stdout.write('\nSummary:')
                self.stdout.write(f'  Total Features: {Feature.objects.count()}')
                self.stdout.write(f'  Total Plans: {SubscriptionPlan.objects.count()}')
                self.stdout.write('\nPlans:')
                for plan in SubscriptionPlan.objects.all():
                    feature_count = plan.planfeature_set.filter(is_enabled=True).count()
                    self.stdout.write(f'  - {plan.name}: ${plan.price}/month, {feature_count} features')
                
                self.stdout.write('\n' + self.style.WARNING('Note: Remember to set stripe_price_id in admin for Regular and Custom plans!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error seeding data: {str(e)}'))
            raise
