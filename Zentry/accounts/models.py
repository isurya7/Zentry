from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pfp = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)
    profession = models.CharField(max_length=100, blank=True)
    total_points = models.IntegerField(default=0)
    daily_points = models.IntegerField(default=0)  # Points earned today
    weekly_points = models.IntegerField(default=0)  # Points earned this week
    current_streak = models.IntegerField(default=0)  # Current journal streak
    longest_streak = models.IntegerField(default=0)  # Longest journal streak
    last_journal_date = models.DateField(blank=True, null=True)  # Last journal entry date
    last_point_award_date = models.DateField(blank=True, null=True)  # Last date points were awarded
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    show_vision_publicly = models.BooleanField(default=True)
    show_task_publicly = models.BooleanField(default=True)
    gmail_email = models.EmailField(blank=True, null=True)
    oauth_token = models.TextField(blank=True, null=True)
    friends = models.ManyToManyField('self', symmetrical=False, related_name='friend_of', blank=True)
    blocked_users = models.ManyToManyField('self', symmetrical=False, related_name='blocked_by', blank=True)
    is_deactivated = models.BooleanField(default=False)
    deactivation_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_profile')
        ]

    def __str__(self):
        return f"{self.user.username}'s Profile"

class FriendRequest(models.Model):
    from_user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['from_user', 'to_user']
        
    def __str__(self):
        return f"Friend request from {self.from_user} to {self.to_user}"