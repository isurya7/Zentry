# social/admin.py
from django.contrib import admin
from .models import AchievementPost, PostComment, PostShare, UserReport

@admin.register(AchievementPost)
class AchievementPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'achievement_type', 'points_earned', 'created_at', 'is_public')
    list_filter = ('achievement_type', 'is_public', 'created_at')
    search_fields = ('title', 'content', 'user__username')
    raw_id_fields = ('user', 'likes')

@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    search_fields = ('content', 'user__username', 'post__title')

@admin.register(PostShare)
class PostShareAdmin(admin.ModelAdmin):
    list_display = ('user', 'original_post', 'shared_at')
    search_fields = ('user__username', 'original_post__title')

@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'reported_user', 'reason', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('reporter__username', 'reported_user__username', 'reason')