# Migration to add location indexes for Restaurant model (Haversine distance calculations)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant', '0004_alter_restaurant_owner'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='restaurant',
            index=models.Index(fields=['latitude', 'longitude'], name='restaurant_location_idx'),
        ),
    ]
