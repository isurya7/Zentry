from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

class VisionBoard(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('achieved', 'Achieved'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vision_boards')
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Detail about your vision")
    cover_image = models.ImageField(upload_to='visions/', blank=True, null=True)
    points = models.IntegerField(default=20, help_text="Points awarded when achieved (minimum 20)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_public = models.BooleanField(default=True, help_text="Make this vision board public or private")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    achieved_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def get_absolute_url(self):
        return reverse('visionboard:view_vision', args=[str(self.id)])
    
    def get_progress_percentage(self):
        """Calculate progress based on completed checkpoints"""
        total_checkpoints = self.checkpoints.count()
        if total_checkpoints == 0:
            return 0
        completed = self.checkpoints.filter(completed=True).count()
        return int((completed / total_checkpoints) * 100)
    
    def all_checkpoints_completed(self):
        """Check if all checkpoints are completed"""
        checkpoints = self.checkpoints.all()
        if not checkpoints.exists():
            return False
        return all(checkpoint.completed for checkpoint in checkpoints)


class Checkpoint(models.Model):
    """Roadmap checkpoints for a vision board"""
    vision_board = models.ForeignKey(VisionBoard, on_delete=models.CASCADE, related_name='checkpoints')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Optional description for this checkpoint")
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    order = models.IntegerField(default=0, help_text="Order/position in the roadmap")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['vision_board', 'order']
    
    def __str__(self):
        return f"{self.title} - {self.vision_board.title}"
    
    def mark_complete(self):
        """Mark checkpoint as complete"""
        if not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
            self.save()
    
    def mark_incomplete(self):
        """Mark checkpoint as incomplete"""
        if self.completed:
            self.completed = False
            self.completed_at = None
            self.save()


class VisionReaction(models.Model):
    vision_board = models.ForeignKey(VisionBoard, on_delete=models.CASCADE, related_name='reactions')
    reactor = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)


class VisionComment(models.Model):
    vision_board = models.ForeignKey(VisionBoard, on_delete=models.CASCADE, related_name='comments')
    commenter = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
