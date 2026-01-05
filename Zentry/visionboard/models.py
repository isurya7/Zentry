from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Vision(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    image = models.ImageField(upload_to='visions/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_achieved = models.BooleanField(default=False)
    achieved_at = models.DateTimeField(blank=True, null=True)
    is_public = models.BooleanField(default=True)

class VisionReaction(models.Model):
    vision = models.ForeignKey(Vision, on_delete=models.CASCADE)
    reactor = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=20)

class VisionComment(models.Model):
    vision = models.ForeignKey(Vision, on_delete=models.CASCADE)
    commenter = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
