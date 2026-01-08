from django.contrib import admin
from .models import VisionBoard, Checkpoint, VisionReaction, VisionComment

@admin.register(VisionBoard)
class VisionBoardAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'points', 'is_public', 'created_at', 'achieved_at')
    list_filter = ('status', 'is_public', 'created_at', 'achieved_at')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'achieved_at')
    date_hierarchy = 'created_at'

@admin.register(Checkpoint)
class CheckpointAdmin(admin.ModelAdmin):
    list_display = ('title', 'vision_board', 'order', 'completed', 'completed_at', 'created_at')
    list_filter = ('completed', 'created_at', 'completed_at')
    search_fields = ('title', 'description', 'vision_board__title')
    readonly_fields = ('created_at', 'completed_at')

@admin.register(VisionReaction)
class VisionReactionAdmin(admin.ModelAdmin):
    list_display = ('vision_board', 'reactor', 'reaction_type', 'created_at')
    list_filter = ('reaction_type', 'created_at')
    search_fields = ('vision_board__title', 'reactor__username')

@admin.register(VisionComment)
class VisionCommentAdmin(admin.ModelAdmin):
    list_display = ('vision_board', 'commenter', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('vision_board__title', 'commenter__username', 'text')
    readonly_fields = ('created_at',)
