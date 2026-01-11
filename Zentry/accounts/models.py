from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pfp = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)
    profession = models.CharField(max_length=100, blank=True)
    
    # Points system fields
    total_points = models.IntegerField(default=0)
    daily_points = models.IntegerField(default=0)
    weekly_points = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_journal_date = models.DateField(blank=True, null=True)
    last_point_award_date = models.DateField(blank=True, null=True)
    
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    
    # Privacy settings - ADD THESE FIELDS
    show_points_publicly = models.BooleanField(default=True)
    show_journals_publicly = models.BooleanField(default=True)
    show_visions_publicly = models.BooleanField(default=True)
    show_task_publicly = models.BooleanField(default=True)
    
    # Subscription fields
    subscription_type = models.CharField(max_length=20, choices=[
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('premium', 'Premium')
    ], default='free')
    subscription_ends = models.DateTimeField(null=True, blank=True)
    
    # Task limits
    max_daily_tasks = models.IntegerField(default=5)
    daily_tasks_count = models.IntegerField(default=0)
    last_task_reset = models.DateField(default=timezone.now)
    
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
    
    def can_add_task(self):
        """Check if user can add more tasks based on subscription"""
        today = timezone.now().date()
        
        # Reset daily count if new day
        if self.last_task_reset != today:
            self.daily_tasks_count = 0
            self.last_task_reset = today
            self.save()
        
        if self.subscription_type == 'free':
            return self.daily_tasks_count < self.max_daily_tasks
        return True  # Pro/Premium users have unlimited
    
    def add_task_attempt(self):
        """Increment task count when adding a task"""
        if self.subscription_type == 'free':
            self.daily_tasks_count += 1
            self.save()

class FriendRequest(models.Model):
    from_user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_requests')
    to_user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['from_user', 'to_user']
        
    def __str__(self):
        return f"Friend request from {self.from_user} to {self.to_user}"