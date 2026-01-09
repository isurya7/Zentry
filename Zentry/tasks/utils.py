from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
from notifications.models import Notification

def award_points(user, points, activity_type='task'):
    """Award points to user and update their profile"""
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Update total points
    old_total = profile.total_points
    profile.total_points += points
    
    # Update daily points
    today = timezone.now().date()
    if not hasattr(profile, 'last_point_award_date') or profile.last_point_award_date != today:
        # Reset daily points if new day
        profile.daily_points = 0
    
    profile.daily_points += points
    profile.last_point_award_date = today
    
    # Update weekly points
    start_of_week = today - timedelta(days=today.weekday())
    # For simplicity, we'll recalculate weekly points in dashboard
    # But we can track it here if needed
    
    profile.save()
    
    # Create notification for points milestones
    milestones = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
    for milestone in milestones:
        if old_total < milestone <= profile.total_points:
            try:
                Notification.objects.create(
                    recipient=user,
                    title=f"🎉 {milestone} Points Milestone!",
                    message=f"Congratulations! You've reached {milestone} total points!",
                    notification_type='points',
                    link='/dashboard/'
                )
            except:
                pass  # Notifications might not be migrated yet
    
    return profile

def check_streak_reminder(user):
    """Check if user needs a streak reminder - sends reminder if no journal today and it's getting late"""
    from journal.models import JournalEntry
    
    profile, created = UserProfile.objects.get_or_create(user=user)
    today = timezone.now().date()
    
    if profile.current_streak > 0 and profile.last_journal_date:
        # Check if streak is about to break (no journal today and it's getting late)
        has_journal_today = JournalEntry.objects.filter(
            user=user,
            date=today
        ).exists()
        
        if not has_journal_today:
            # Check if it's afternoon/evening - time to remind
            from datetime import datetime
            current_hour = datetime.now().hour
            
            # Send reminder after 3 PM (15:00) - earlier reminder
            if current_hour >= 15:  # 3 PM
                # Check if we already sent reminder today
                existing_notification = Notification.objects.filter(
                    recipient=user,
                    notification_type='streak_warning',
                    created_at__date=today
                ).exists()
                
                if not existing_notification:
                    try:
                        Notification.objects.create(
                            recipient=user,
                            title=f"🔥 Don't Break Your {profile.current_streak} Day Streak!",
                            message=f"You have a {profile.current_streak} day journal streak. Create a journal entry today before midnight to keep it going!",
                            notification_type='streak_warning',
                            link='/journal/create/'
                        )
                    except:
                        pass  # Notifications might not be migrated yet
                    
                    return True
    
    return False

