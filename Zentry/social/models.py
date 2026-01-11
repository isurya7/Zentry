# social/models.py - FINAL VERSION
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class AchievementPost(models.Model):
    """Posts users can make about their achievements/stats"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievement_posts')
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='achievements/', blank=True, null=True)
    points_earned = models.IntegerField(default=0)
    achievement_type = models.CharField(max_length=50, choices=[
        ('task', 'Task Completed'),
        ('journal', 'Journal Entry'),
        ('streak', 'Streak Milestone'),
        ('points', 'Points Milestone'),
        ('vision', 'Vision Achieved'),
        ('custom', 'Custom Achievement'),
    ], default='custom')
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    is_public = models.BooleanField(default=True)
    tags = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def get_tags_list(self):
        """Convert comma-separated tags to list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []
    
    def like_count(self):
        """Get number of likes"""
        return self.likes.count()
    
    def comment_count(self):
        """Get number of comments"""
        return self.comments.count()
    
    def share_count(self):
        """Get number of shares"""
        return self.shares.count()


class PostComment(models.Model):
    """Comments on achievement posts"""
    post = models.ForeignKey(AchievementPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.post.title}"
    
    def like_count(self):
        """Get number of likes on comment"""
        return self.likes.count()


class PostShare(models.Model):
    """Track when users share posts"""
    original_post = models.ForeignKey(AchievementPost, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_posts')
    shared_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-shared_at']
        unique_together = ['original_post', 'user']  # Prevent duplicate shares
    
    def __str__(self):
        return f"{self.user.username} shared {self.original_post.title}"


class UserReport(models.Model):
    """User reporting system"""
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['reporter', 'reported_user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report on {self.reported_user.username} by {self.reporter.username}"