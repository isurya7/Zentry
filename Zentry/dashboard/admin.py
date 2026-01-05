from django.contrib import admin
from .models import DashboardStats

@admin.register(DashboardStats)
class DashboardStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'important_emails_week', 'pending_tasks_count', 'last_updated')
    search_fields = ('user__username',)
    readonly_fields = ('last_updated',)