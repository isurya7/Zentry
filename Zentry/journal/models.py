from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

class JournalEntry(models.Model):
    MOOD_CHOICES = [
        ('', 'Select Mood'),
        ('happy', '😊 Happy'),
        ('sad', '😢 Sad'),
        ('excited', '🤩 Excited'),
        ('angry', '😠 Angry'),
        ('peaceful', '😌 Peaceful'),
        ('anxious', '😰 Anxious'),
        ('tired', '😴 Tired'),
        ('productive', '💪 Productive'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    cover_image = models.ImageField(upload_to='journals/', blank=True, null=True)
    content = models.TextField()
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False)
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    points_earned = models.IntegerField(default=5)  # Base 5 points for journal entry
    word_points_earned = models.IntegerField(default=0)  # Points from discovered words
    streak_points_earned = models.IntegerField(default=0)  # Points from streak milestones
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Journal entries"
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def get_absolute_url(self):
        return reverse('journal:view_journal', args=[str(self.id)])
    
    def get_tags_list(self):
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []
    
    def get_total_points_earned(self):
        """Get total points earned from this journal entry"""
        return self.points_earned + self.word_points_earned + self.streak_points_earned


class DiscoveredWord(models.Model):
    """Track words discovered in journal entries with their meanings"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discovered_words')
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='words', null=True, blank=True)
    word = models.CharField(max_length=100)
    meaning = models.TextField(blank=True, help_text="Word meaning from Gemini API")
    discovered_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    is_high_level = models.BooleanField(default=False, help_text="High-level word that earns +1 point")
    points_earned = models.IntegerField(default=0)  # Points earned from this word discovery
    
    class Meta:
        ordering = ['-discovered_date', '-created_at']
        unique_together = ['user', 'word']  # Each word discovered only once per user
    
    def __str__(self):
        return f"{self.word} - {self.user.username}"


class PointTransaction(models.Model):
    """Track all point transactions for history"""
    TRANSACTION_TYPES = [
        ('journal_entry', 'Journal Entry'),
        ('word_discovery', 'Word Discovery'),
        ('streak_milestone', 'Streak Milestone'),
        ('task_completion', 'Task Completion'),
        ('vision_achieved', 'Vision Achieved'),
        ('journal_deleted', 'Journal Deleted'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    points = models.IntegerField()  # Positive for earned, negative for deducted
    description = models.CharField(max_length=500, help_text="What earned/deducted these points")
    reference_id = models.IntegerField(null=True, blank=True, help_text="ID of the related object (journal, task, etc.)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        sign = '+' if self.points > 0 else ''
        return f"{sign}{self.points} points - {self.get_transaction_type_display()} - {self.user.username}"
