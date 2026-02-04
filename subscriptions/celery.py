from celery import Celery
import os

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hungryBird.settings')

# Create Celery app
app = Celery('subscriptions')

# Load configuration from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from installed apps
app.autodiscover_tasks(['subscriptions'])

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration"""
    print(f'Request: {self.request!r}')
