from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New fields for enhanced features
    is_pinned = models.BooleanField(default=False)
    color = models.CharField(max_length=7, default='#1e293b')  # HEX color
    tags = models.CharField(max_length=255, blank=True)  # Comma-separated tags
    
    class Meta:
        ordering = ['-is_pinned', '-updated_at']
    
    def save(self, *args, **kwargs):
        # Auto-generate title from first line if empty
        if not self.title and self.content:
            first_line = self.content.split('\n')[0].strip()
            self.title = first_line[:197] + '...' if len(first_line) > 200 else first_line
        super().save(*args, **kwargs)
    
    def get_tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    def word_count(self):
        """Calculate word count"""
        return len(self.content.split())
    
    def reading_time(self):
        """Calculate estimated reading time (200 words per minute)"""
        words = self.word_count()
        minutes = max(1, words // 200)
        return f"{minutes} min read"