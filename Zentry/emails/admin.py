from django.contrib import admin
from .models import GmailAccount, Email, EmailStats

@admin.register(GmailAccount)
class GmailAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "token_expiry")
    list_select_related = ('user',)  # Optimize database queries
    search_fields = ("user__username", "email")

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ("subject", "sender", "gmail_account", "received_at", "is_important", "is_resolved")
    list_filter = ("is_important", "is_resolved", "received_at")
    search_fields = ("subject", "sender", "snippet")
    list_select_related = ('gmail_account',)  # Optimize database queries
    date_hierarchy = 'received_at'  # Add date-based navigation

@admin.register(EmailStats)
class EmailStatsAdmin(admin.ModelAdmin):
    list_display = ("gmail_account", "total_emails", "solved_emails", "pending_emails")
    list_select_related = ('gmail_account',)  # Optimize database queries
    
    def has_add_permission(self, request):
        # Prevent manually adding stats - they should be auto-created
        return False