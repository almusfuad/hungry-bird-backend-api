# Migration to add location indexes for User model (Haversine distance calculations)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authUser', '0006_user_stripe_customer_id'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['latitude', 'longitude'], name='user_location_idx'),
        ),
    ]
