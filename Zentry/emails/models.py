from django.db import models
from django.contrib.auth.models import User

class GmailAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField()
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expiry = models.DateTimeField()

    def __str__(self):
        return self.email


class Email(models.Model):
    gmail_account = models.ForeignKey(
        GmailAccount, 
        on_delete=models.CASCADE,
        related_name='emails',
        null=True,  # Add this temporarily
        blank=True  # Added related_name to resolve conflict
    )
    message_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    thread_id = models.CharField(max_length=255)
    sender = models.EmailField()
    subject = models.CharField(max_length=255)
    snippet = models.TextField(null=True, blank=True)
    body = models.TextField(blank=True, null=True)
    received_at = models.DateTimeField(null=True, blank=True)
    is_important = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return self.subject

    class Meta:
        ordering = ['-received_at']  # Added ordering for better query results


class EmailStats(models.Model):
    gmail_account = models.OneToOneField(
        GmailAccount, 
        on_delete=models.CASCADE,
        related_name='stats'  # Added related_name for consistency
    )
    total_emails = models.IntegerField(default=0)
    solved_emails = models.IntegerField(default=0)
    pending_emails = models.IntegerField(default=0)

    def update_stats(self):
        self.total_emails = self.gmail_account.emails.count()  # Use the new related_name
        self.solved_emails = self.gmail_account.emails.filter(is_resolved=True).count()
        self.pending_emails = self.total_emails - self.solved_emails
        self.save()

    def __str__(self):
        return f"Stats for {self.gmail_account.email}"