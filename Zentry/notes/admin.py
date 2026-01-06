from django.contrib import admin
from .models import Note

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_at', 'updated_at', 'is_pinned']
    list_filter = ['created_at', 'updated_at', 'is_pinned']
    search_fields = ['title', 'content', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']