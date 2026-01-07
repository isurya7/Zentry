from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, datetime, time
import uuid

class DailyTask(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    cover_image = models.ImageField(upload_to='tasks/', blank=True, null=True)
    date = models.DateField()
    is_public = models.BooleanField(default=False)
    group_task = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    points = models.IntegerField(default=1)  # Auto-assigned +1 point per task
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Reminder fields
    reminder_time = models.TimeField(default=time(20, 0))  # Default 8 PM reminder
    reminder_sent = models.BooleanField(default=False)
    reminder_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    def __str__(self):
        return f"{self.title} - {self.date}"
    
    @property
    def is_due_today(self):
        return self.date == timezone.now().date()
    
    @property
    def should_send_reminder(self):
        """Check if reminder should be sent today"""
        if self.completed or self.reminder_sent:
            return False
        
        today = timezone.now().date()
        task_time = datetime.combine(self.date, self.reminder_time)
        reminder_time = timezone.make_aware(task_time)
        
        # Send reminder if task is today and reminder time has passed
        return self.date == today and timezone.now() >= reminder_time

class TaskMember(models.Model):
    task = models.ForeignKey(DailyTask, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('joined', 'Joined'), ('completed', 'Completed')])
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['task', 'user']

class TaskReminder(models.Model):
    task = models.ForeignKey(DailyTask, on_delete=models.CASCADE, related_name='reminders')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)
    reminder_type = models.CharField(max_length=20, choices=[
        ('daily', 'Daily Reminder'),
        ('overdue', 'Overdue Task'),
        ('invitation', 'Task Invitation')
    ])
    
    class Meta:
        ordering = ['-sent_at']