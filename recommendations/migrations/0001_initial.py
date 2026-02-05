# Generated migration for RecommendationLog model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('authUser', '0006_user_stripe_customer_id'),
        ('restaurant', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecommendationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('recommendation_type', models.IntegerField(choices=[(1, 'Nearby Restaurant'), (2, 'Popular Item'), (3, 'Personalized')], help_text='Type of recommendation shown to the user')),
                ('user_latitude', models.DecimalField(decimal_places=6, max_digits=9, help_text='User latitude at the time of recommendation')),
                ('user_longitude', models.DecimalField(decimal_places=6, max_digits=9, help_text='User longitude at the time of recommendation')),
                ('search_radius', models.DecimalField(decimal_places=2, default=10.0, help_text='Search radius in kilometers used for the recommendation', max_digits=5)),
                ('was_clicked', models.BooleanField(default=False, help_text='Whether the user clicked/interacted with this recommendation')),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='recommendation_logs', to='authUser.user')),
                ('menu_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='recommendation_logs', to='restaurant.menuitem')),
                ('restaurant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='recommendation_logs', to='restaurant.restaurant')),
            ],
            options={
                'verbose_name': 'Recommendation Log',
                'verbose_name_plural': 'Recommendation Logs',
                'db_table': 'recommendation_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='recommendationlog',
            index=models.Index(fields=['created_at', 'recommendation_type'], name='rec_log_created_type_idx'),
        ),
        migrations.AddIndex(
            model_name='recommendationlog',
            index=models.Index(fields=['customer'], name='rec_log_customer_idx'),
        ),
    ]
