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
    discovered_words = models.TextField(blank=True, help_text="Comma-separated list of new words discovered")
    points_earned = models.IntegerField(default=1)  # Points for creating journal
    
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