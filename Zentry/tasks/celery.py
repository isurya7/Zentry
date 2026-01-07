from celery import Celery
from celery.schedules import crontab

app = Celery('zentry')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    'send-daily-reminders': {
        'task': 'tasks.tasks.send_reminders',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}