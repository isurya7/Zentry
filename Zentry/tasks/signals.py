from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import DailyTask, TaskReminder

@receiver(post_save, sender=DailyTask)
def schedule_reminder(sender, instance, created, **kwargs):
    """
    Schedule a reminder when a task is created or updated
    In production, this would schedule a Celery task
    """
    if created and not instance.completed:
        # In production: schedule_reminder_task.delay(instance.id)
        pass