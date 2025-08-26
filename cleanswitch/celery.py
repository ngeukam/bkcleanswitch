# cleanswitch/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cleanswitch.settings')

app = Celery('cleanswitch')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps
app.autodiscover_tasks()

# Configure beat schedule
app.conf.beat_schedule = {
    'generate-recurring-tasks': {
        'task': 'TaskServices.tasks.generate_recurring_tasks',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}