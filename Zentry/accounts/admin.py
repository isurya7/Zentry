from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, FriendRequest

# Define an inline admin descriptor for UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

# Define a new User admin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_user_profile_status')
    
    def get_user_profile_status(self, obj):
        try:
            return "Active" if not obj.userprofile.is_deactivated else "Deactivated"
        except UserProfile.DoesNotExist:
            return "No Profile"
    get_user_profile_status.short_description = 'Profile Status'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# UserProfile Admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_full_name', 'profession', 'total_points', 'is_deactivated')
    list_filter = ('is_deactivated', 'profession')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'profession')
    
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_full_name.short_description = 'Full Name'

# FriendRequest Admin
@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ('from_user', 'to_user', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('from_user__user__username', 'to_user__user__username')