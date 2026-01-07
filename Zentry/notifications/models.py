from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Notification(models.Model):
    """Notification system for users"""
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=[
        ('task_reminder', 'Task Reminder'),
        ('streak_warning', 'Streak Warning'),
        ('friend_request', 'Friend Request'),
        ('message', 'New Message'),
        ('achievement', 'Achievement'),
        ('points', 'Points Milestone'),
        ('system', 'System'),
    ], default='system', blank=True)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    link = models.URLField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    
    # Alias for compatibility
    @property
    def user(self):
        return self.recipient
