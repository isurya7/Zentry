from django.db import models
from django.contrib.auth.models import User


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
    points = models.IntegerField(default=0)

class TaskMember(models.Model):
    task = models.ForeignKey(DailyTask, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('joined', 'Joined'), ('completed', 'Completed')])