from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Conversation(models.Model):
    """Direct message conversation between two users"""
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation {self.id}"
    
    def get_other_user(self, user):
        """Get the other participant in the conversation"""
        return self.participants.exclude(id=user.id).first()

class Message(models.Model):
    """Direct messages between users"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    room = models.ForeignKey('ChatRoom', on_delete=models.CASCADE, null=True, blank=True)  # Keep for backward compatibility
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message from {self.sender.username}"

# Keep ChatRoom for group chats (optional)
class ChatRoom(models.Model):
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(User)
