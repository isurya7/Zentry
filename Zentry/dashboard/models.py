from django.db import models
from django.contrib.auth.models import User

class DashboardStats(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    important_emails_week = models.IntegerField(default=0)
    important_emails_month = models.IntegerField(default=0)
    unread_emails_count = models.IntegerField(default=0)
    pending_tasks_count = models.IntegerField(default=0)
    completed_tasks_week = models.IntegerField(default=0)
    completed_tasks_month = models.IntegerField(default=0)
    journal_entries_week = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Stats for {self.user.username}"