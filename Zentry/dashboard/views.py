from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta, datetime
from accounts.models import UserProfile
from tasks.models import DailyTask
from journal.models import JournalEntry, PointTransaction, DiscoveredWord
from notifications.models import Notification
from tasks.utils import check_streak_reminder
from django.db.models import Sum, Count

@login_required
def dashboard(request):
    # Always try to fetch or create the user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    # Calculate points from all activities
    # Tasks completed today
    tasks_today = DailyTask.objects.filter(
        creator=request.user,
        completed=True,
        completed_at__date=today
    )
    task_points_today = tasks_today.aggregate(total=Sum('points'))['total'] or 0
    
    # Tasks completed this week
    tasks_week = DailyTask.objects.filter(
        creator=request.user,
        completed=True,
        completed_at__date__gte=start_of_week
    )
    task_points_week = tasks_week.aggregate(total=Sum('points'))['total'] or 0
    
    # Tasks completed this month
    tasks_month = DailyTask.objects.filter(
        creator=request.user,
        completed=True,
        completed_at__date__gte=start_of_month
    )
    task_points_month = tasks_month.aggregate(total=Sum('points'))['total'] or 0
    
    # Journals created today
    journals_today = JournalEntry.objects.filter(
        user=request.user,
        created_at__date=today
    )
    journal_points_today = journals_today.aggregate(total=Sum('points_earned'))['total'] or 0
    
    # Journals created this week
    journals_week = JournalEntry.objects.filter(
        user=request.user,
        created_at__date__gte=start_of_week
    )
    journal_points_week = journals_week.aggregate(total=Sum('points_earned'))['total'] or 0
    
    # Total points today (tasks + journals)
    total_points_today = task_points_today + journal_points_today
    
    # Total points this week
    total_points_week = task_points_week + journal_points_week
    
    # Update profile daily/weekly points if needed
    if profile.daily_points != total_points_today:
        profile.daily_points = total_points_today
    if profile.weekly_points != total_points_week:
        profile.weekly_points = total_points_week
    profile.save()
    
    # Check streak reminders
    check_streak_reminder(request.user)
    
    # Get notifications
    notifications = Notification.objects.filter(recipient=request.user, is_read=False).order_by('-timestamp')[:10]
    unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    # Performance graph data (current month - points vs days)
    from calendar import monthrange
    year = today.year
    month = today.month
    days_in_month = monthrange(year, month)[1]
    
    performance_data = []
    for day in range(1, days_in_month + 1):
        date = today.replace(day=day)
        if date > today:
            break  # Don't include future dates
        
        day_tasks = DailyTask.objects.filter(
            creator=request.user,
            completed=True,
            completed_at__date=date
        )
        day_journals = JournalEntry.objects.filter(
            user=request.user,
            created_at__date=date
        )
        # Calculate actual points (not just count)
        # Each completed task = +1 point
        task_points = day_tasks.aggregate(total=Sum('points'))['total'] or day_tasks.count()
        journal_points = day_journals.aggregate(total=Sum('points_earned'))['total'] or day_journals.count()
        day_points = task_points + journal_points
        
        performance_data.append({
            'date': date.strftime('%d'),
            'day': day,
            'points': day_points,
            'tasks': day_tasks.count(),
            'journals': day_journals.count(),
        })
    
    # Convert to JSON for template
    import json
    performance_data_json = json.dumps(performance_data)
    
    # Get leaderboard data (top 10 users by total points)
    from django.contrib.auth.models import User
    top_users = UserProfile.objects.filter(
        total_points__gt=0
    ).order_by('-total_points')[:10]
    
    # Get current user's rank
    user_rank = UserProfile.objects.filter(total_points__gt=profile.total_points).count() + 1
    
    # Get pending tasks
    pending_tasks = DailyTask.objects.filter(
        creator=request.user,
        completed=False,
        date__gte=today
    ).order_by('date')[:5]
    
    # Get recent completed tasks
    recent_completed = DailyTask.objects.filter(
        creator=request.user,
        completed=True
    ).order_by('-completed_at')[:5]
    
    # Get unread messages count
    try:
        from messaging.models import Conversation, Message
        user_conversations = Conversation.objects.filter(participants=request.user)
        unread_messages_count = Message.objects.filter(
            conversation__in=user_conversations,
            is_read=False
        ).exclude(sender=request.user).count()
    except:
        unread_messages_count = 0

    # Get recent points transactions
    recent_transactions = PointTransaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Get word discovery stats
    total_words = DiscoveredWord.objects.filter(user=request.user).count()
    high_level_words = DiscoveredWord.objects.filter(user=request.user, is_high_level=True).count()
    word_points_total = DiscoveredWord.objects.filter(user=request.user).aggregate(total=Sum('points_earned'))['total'] or 0
    recent_words = DiscoveredWord.objects.filter(user=request.user).order_by('-discovered_date', '-created_at')[:5]
    
    # Pass context to the template
    context = {
        'profile': profile,
        'stats': {
            'important_emails_week': 0,
            'important_emails_month': 0,
            'unread_emails_count': 0,
            'pending_tasks_count': pending_tasks.count(),
            'unread_messages_count': unread_messages_count,
            'completed_tasks_week': tasks_week.count(),
            'completed_tasks_month': tasks_month.count(),
            'journal_entries_week': journals_week.count(),
            'task_points_today': task_points_today,
            'journal_points_today': journal_points_today,
            'total_points_today': total_points_today,
            'task_points_week': task_points_week,
            'journal_points_week': journal_points_week,
            'total_points_week': total_points_week,
        'task_points_month': task_points_month,
        'current_streak': profile.current_streak,
        'longest_streak': profile.longest_streak,
        },
        'pending_tasks': pending_tasks,
        'recent_completed': recent_completed,
        'important_emails': [],
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'performance_data': performance_data_json,
        'leaderboard': top_users,
        'user_rank': user_rank,
        'recent_transactions': recent_transactions,
        'total_words': total_words,
        'high_level_words': high_level_words,
        'word_points_total': word_points_total,
        'recent_words': recent_words,
    }
    return render(request, 'dashboard/dashboard.html', context)