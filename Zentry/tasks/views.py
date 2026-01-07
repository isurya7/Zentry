from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db import models
from datetime import datetime, timedelta, date
from .models import DailyTask, TaskMember, TaskReminder
from .forms import DailyTaskForm, TaskReminderForm
from .utils import award_points
import json

# ------------------ TASK VIEWS ------------------

@login_required
def create_task(request):
    if request.method == 'POST':
        form = DailyTaskForm(request.POST, request.FILES)
        if form.is_valid():
            task = form.save(commit=False)
            task.creator = request.user
            task.save()
            
            # If it's a group task, add creator as member
            if task.group_task:
                TaskMember.objects.create(
                    task=task,
                    user=request.user,
                    status='joined'
                )
            
            messages.success(request, 'Task created successfully!')
            return redirect('tasks:view_task', task_id=task.id)
    else:
        form = DailyTaskForm()
    
    return render(request, 'tasks/create_task.html', {
        'form': form,
        'title': 'Create New Task'
    })

@login_required
def view_task(request, task_id):
    task = get_object_or_404(DailyTask, id=task_id)
    
    # Check if user can view task
    if not task.is_public and task.creator != request.user:
        if not TaskMember.objects.filter(task=task, user=request.user).exists():
            return HttpResponseForbidden("You don't have permission to view this task.")
    
    is_member = TaskMember.objects.filter(task=task, user=request.user).exists()
    is_creator = task.creator == request.user
    members = TaskMember.objects.filter(task=task).select_related('user')
    
    return render(request, 'tasks/view_task.html', {
        'task': task,
        'is_creator': is_creator,
        'is_member': is_member,
        'members': members,
        'today': timezone.now().date()
    })

@login_required
def edit_task(request, task_id):
    task = get_object_or_404(DailyTask, id=task_id)
    
    if task.creator != request.user:
        return HttpResponseForbidden("You can only edit your own tasks.")
    
    if request.method == 'POST':
        form = DailyTaskForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully!')
            return redirect('tasks:view_task', task_id=task.id)
    else:
        form = DailyTaskForm(instance=task)
    
    return render(request, 'tasks/create_task.html', {
        'form': form,
        'title': 'Edit Task',
        'task': task
    })

@login_required
def delete_task(request, task_id):
    task = get_object_or_404(DailyTask, id=task_id)
    
    if task.creator != request.user:
        return HttpResponseForbidden("You can only delete your own tasks.")
    
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted successfully!')
        return redirect('tasks:task_dashboard')
    
    return render(request, 'tasks/confirm_delete.html', {'task': task})

@login_required
def mark_task_complete(request, task_id):
    task = get_object_or_404(DailyTask, id=task_id)
    
    # Check if user can complete this task
    if task.group_task:
        member = TaskMember.objects.filter(task=task, user=request.user).first()
        if not member:
            return HttpResponseForbidden("You're not a member of this task.")
        
        member.status = 'completed'
        member.save()
        
        # Check if all members have completed
        all_completed = not TaskMember.objects.filter(
            task=task, 
            status__in=['pending', 'joined']
        ).exists()
        
        if all_completed:
            task.completed = True
            task.completed_at = timezone.now()
            task.points = 1  # Auto-assign +1 point
            task.save()
            # Award points to creator
            award_points(task.creator, 1, 'task')
    else:
        if task.creator != request.user:
            return HttpResponseForbidden("You can only complete your own tasks.")
        
        task.completed = True
        task.completed_at = timezone.now()
        task.points = 1  # Auto-assign +1 point
        task.save()
        # Award points to user
        profile = award_points(request.user, 1, 'task')
        
        # Create achievement post automatically
        try:
            from social.models import AchievementPost
            AchievementPost.objects.create(
                user=request.user,
                title=f"Completed: {task.title}",
                content=f"I just completed my task '{task.title}' and earned +1 point! 🎉",
                achievement_type='task',
                points_earned=1,
                is_public=task.is_public
            )
        except:
            pass  # Social app might not be migrated yet
    
    messages.success(request, 'Task marked as complete! +1 point earned!')
    return redirect('tasks:view_task', task_id=task.id)

@login_required
def invite_friends(request, task_id):
    task = get_object_or_404(DailyTask, id=task_id)
    
    if task.creator != request.user:
        return HttpResponseForbidden("Only task creator can invite friends.")
    
    if not task.group_task:
        messages.error(request, 'This task is not a group task.')
        return redirect('tasks:view_task', task_id=task.id)
    
    if request.method == 'POST':
        friend_ids = request.POST.getlist('friends')
        for friend_id in friend_ids:
            user = User.objects.get(id=friend_id)
            TaskMember.objects.get_or_create(
                task=task,
                user=user,
                defaults={'status': 'pending'}
            )
        messages.success(request, 'Invitations sent successfully!')
        return redirect('tasks:view_task', task_id=task.id)
    
    # Get user's friends (you might want to implement a proper friends system)
    friends = User.objects.exclude(id=request.user.id)[:10]  # Simplified
    
    return render(request, 'tasks/invite_friends.html', {
        'task': task,
        'friends': friends
    })

@login_required
def task_calendar(request):
    # Get all tasks for the user
    user_tasks = DailyTask.objects.filter(creator=request.user)
    member_tasks = DailyTask.objects.filter(
        taskmember__user=request.user,
        taskmember__status__in=['joined', 'completed']
    )
    all_tasks = user_tasks | member_tasks
    
    # Format for calendar
    calendar_events = []
    for task in all_tasks.distinct():
        calendar_events.append({
            'title': task.title,
            'start': task.date.isoformat(),
            'url': f'/tasks/{task.id}/',
            'backgroundColor': '#6d28d9' if task.completed else '#ef4444',
            'borderColor': '#6d28d9' if task.completed else '#ef4444',
            'extendedProps': {
                'completed': task.completed,
                'points': task.points
            }
        })
    
    return render(request, 'tasks/calendar.html', {
        'events': json.dumps(calendar_events),
        'title': 'Task Calendar'
    })

@login_required
def weekly_summary(request):
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Get tasks for this week
    user_tasks = DailyTask.objects.filter(
        creator=request.user,
        date__range=[start_of_week, end_of_week]
    )
    
    member_tasks = DailyTask.objects.filter(
        taskmember__user=request.user,
        taskmember__status__in=['joined', 'completed'],
        date__range=[start_of_week, end_of_week]
    )
    
    all_tasks = user_tasks | member_tasks
    
    # Calculate statistics
    total_tasks = all_tasks.distinct().count()
    completed_tasks = all_tasks.filter(completed=True).count()
    # Each completed task = +1 point
    total_points = sum(task.points for task in all_tasks.filter(completed=True)) or completed_tasks
    
    # Group by day and calculate points
    daily_stats = {}
    max_points = 0
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_tasks = all_tasks.filter(date=day)
        completed_day_tasks = day_tasks.filter(completed=True)
        # Each completed task = +1 point
        day_points = sum(task.points for task in completed_day_tasks) or completed_day_tasks.count()
        if day_points > max_points:
            max_points = day_points
        daily_stats[day] = {
            'total': day_tasks.count(),
            'completed': completed_day_tasks.count(),
            'points': day_points
        }
    
    return render(request, 'tasks/weekly_summary.html', {
        'start_date': start_of_week,
        'end_date': end_of_week,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        'total_points': total_points or completed_tasks,
        'daily_stats': daily_stats,
        'weekly_max': max_points or 1,
        'title': 'Weekly Summary'
    })

# ------------------ NEW REMINDER FEATURES ------------------

@login_required
def task_dashboard(request):
    """Main dashboard showing today's tasks and upcoming reminders"""
    today = timezone.now().date()
    
    # Get today's tasks (excluding completed)
    today_tasks = DailyTask.objects.filter(
        creator=request.user,
        date=today,
        completed=False
    ).order_by('reminder_time')
    
    # Get group tasks where user is a member (excluding completed)
    member_tasks = DailyTask.objects.filter(
        taskmember__user=request.user,
        taskmember__status__in=['joined', 'pending'],
        date=today,
        completed=False
    )
    
    # Combine tasks
    all_today_tasks = (today_tasks | member_tasks).distinct()
    
    # Calculate completed count (for stats only)
    completed_count = DailyTask.objects.filter(
        creator=request.user,
        date=today,
        completed=True
    ).count()
    
    # Get upcoming tasks (next 7 days)
    upcoming_tasks = DailyTask.objects.filter(
        creator=request.user,
        date__range=[today + timedelta(days=1), today + timedelta(days=7)],
        completed=False
    ).order_by('date', 'reminder_time')[:10]
    
    # Get overdue tasks
    overdue_tasks = DailyTask.objects.filter(
        creator=request.user,
        date__lt=today,
        completed=False
    ).order_by('date')
    
    return render(request, 'tasks/dashboard.html', {
        'today_tasks': all_today_tasks,
        'completed_count': completed_count,
        'upcoming_tasks': upcoming_tasks,
        'overdue_tasks': overdue_tasks,
        'today': today,
        'title': 'Task Dashboard'
    })

@login_required
def set_reminder(request, task_id):
    """Set or update reminder for a task"""
    task = get_object_or_404(DailyTask, id=task_id)
    
    if task.creator != request.user:
        return HttpResponseForbidden("You can only set reminders for your own tasks.")
    
    if request.method == 'POST':
        form = TaskReminderForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            task.reminder_sent = False  # Reset reminder when time changes
            task.save()
            messages.success(request, 'Reminder updated successfully!')
            return redirect('tasks:view_task', task_id=task.id)
    else:
        form = TaskReminderForm(instance=task)
    
    return render(request, 'tasks/set_reminder.html', {
        'form': form,
        'task': task,
        'title': 'Set Reminder'
    })

@login_required
def dismiss_reminder(request, task_id, token):
    """Dismiss a reminder (mark as seen)"""
    task = get_object_or_404(DailyTask, id=task_id, reminder_token=token)
    
    # Check if user can dismiss this reminder
    if task.creator != request.user and not TaskMember.objects.filter(task=task, user=request.user).exists():
        return HttpResponseForbidden("You don't have permission to dismiss this reminder.")
    
    task.reminder_sent = True
    task.save()
    
    messages.success(request, 'Reminder dismissed!')
    return redirect('tasks:task_dashboard')

@login_required
def send_test_reminder(request, task_id):
    """Send a test reminder immediately (for testing purposes)"""
    task = get_object_or_404(DailyTask, id=task_id)
    
    if task.creator != request.user:
        return HttpResponseForbidden("You can only send test reminders for your own tasks.")
    
    # Call your reminder sending function here
    # send_task_reminder(task)  # You'll implement this function
    
    messages.success(request, 'Test reminder sent! Check your notifications.')
    return redirect('tasks:view_task', task_id=task.id)

# ------------------ API ENDPOINTS ------------------

@login_required
def api_tasks_today(request):
    """API endpoint for getting today's tasks (for AJAX updates)"""
    today = timezone.now().date()
    
    tasks = DailyTask.objects.filter(
        creator=request.user,
        date=today,
        completed=False
    ).values('id', 'title', 'description', 'reminder_time', 'points', 'completed')
    
    return JsonResponse(list(tasks), safe=False)

@login_required
def api_complete_task(request, task_id):
    """API endpoint for completing tasks via AJAX"""
    if request.method == 'POST':
        task = get_object_or_404(DailyTask, id=task_id, creator=request.user)
        if not task.completed:
            task.completed = True
            task.completed_at = timezone.now()
            task.points = 1  # Auto-assign +1 point
            task.save()
            # Award points
            profile = award_points(request.user, 1, 'task')
        
        return JsonResponse({
            'success': True,
            'points_earned': 1,
            'total_points': profile.total_points,
            'daily_points': profile.daily_points
        })
    
    return JsonResponse({'success': False}, status=400)

# ------------------ REMINDER BACKGROUND TASK ------------------
# This would typically be in a separate file like tasks.py for Celery

def check_and_send_reminders():
    """Function to be called by a scheduled task (Celery beat)"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    
    now = timezone.now()
    today = now.date()
    
    # Find tasks that need reminders
    tasks_to_remind = DailyTask.objects.filter(
        date=today,
        completed=False,
        reminder_sent=False
    ).select_related('creator')
    
    for task in tasks_to_remind:
        task_time = datetime.combine(task.date, task.reminder_time)
        reminder_time = timezone.make_aware(task_time)
        
        if now >= reminder_time:
            # Send reminder
            subject = f"⏰ Reminder: {task.title}"
            html_message = render_to_string('tasks/email/reminder.html', {
                'task': task,
                'user': task.creator
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                'noreply@zentry.com',
                [task.creator.email],
                html_message=html_message,
                fail_silently=False
            )
            
            # Mark as sent
            task.reminder_sent = True
            task.save()
            
            # Create reminder record
            TaskReminder.objects.create(
                task=task,
                user=task.creator,
                reminder_type='daily'
            )

@login_required
def weekly_summary(request):
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Get tasks for this week
    user_tasks = DailyTask.objects.filter(
        creator=request.user,
        date__range=[start_of_week, end_of_week]
    ).order_by('date')
    
    member_tasks = DailyTask.objects.filter(
        taskmember__user=request.user,
        taskmember__status__in=['joined', 'completed'],
        date__range=[start_of_week, end_of_week]
    )
    
    all_tasks = (user_tasks | member_tasks).distinct()
    
    # Calculate statistics
    total_tasks = all_tasks.count()
    completed_tasks = all_tasks.filter(completed=True).count()
    total_points = sum(task.points for task in all_tasks.filter(completed=True))
    
    # Calculate completion time (average)
    completion_times = []
    for task in all_tasks.filter(completed_at__isnull=False):
        if task.completed_at and task.created_at:
            completion_times.append((task.completed_at - task.created_at).total_seconds())
    
    avg_completion_time = "N/A"
    if completion_times:
        avg_seconds = sum(completion_times) / len(completion_times)
        avg_completion_time = format_duration(avg_seconds)
    
    # Group by day for chart
    daily_stats = {}
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_tasks = all_tasks.filter(date=day)
        daily_stats[day] = {
            'total': day_tasks.count(),
            'completed': day_tasks.filter(completed=True).count(),
            'points': sum(task.points for task in day_tasks.filter(completed=True))
        }
    
    # Get weekly max for chart scaling
    weekly_max = max(stats['completed'] for stats in daily_stats.values()) if daily_stats else 1
    
    # Get leaderboard (top users by points this week)
    from django.db.models import Sum
    top_users = User.objects.annotate(
        weekly_points=Sum('dailytask__points', 
                         filter=models.Q(dailytask__date__range=[start_of_week, end_of_week],
                                        dailytask__completed=True))
    ).filter(weekly_points__gt=0).order_by('-weekly_points')[:5]
    
    # Calculate week-over-week changes
    last_start = start_of_week - timedelta(days=7)
    last_end = end_of_week - timedelta(days=7)
    last_week_tasks = DailyTask.objects.filter(
        creator=request.user,
        date__range=[last_start, last_end]
    )
    
    last_total = last_week_tasks.count()
    last_completed = last_week_tasks.filter(completed=True).count()
    last_points = sum(task.points for task in last_week_tasks.filter(completed=True))
    
    # Calculate percentage changes
    task_change = round(((total_tasks - last_total) / last_total * 100) if last_total > 0 else 0, 1)
    completion_change = round(((completed_tasks - last_completed) / last_completed * 100) if last_completed > 0 else 0, 1)
    points_change = round(((total_points - last_points) / last_points * 100) if last_points > 0 else 0, 1)
    
    # Group tasks by day for daily breakdown
    weekly_tasks = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        tasks = all_tasks.filter(date=day).order_by('reminder_time')
        weekly_tasks.append({
            'date': day,
            'tasks': tasks
        })
    
    return render(request, 'tasks/weekly_summary.html', {
        'start_date': start_of_week,
        'end_date': end_of_week,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
        'total_points': total_points,
        'avg_completion_time': avg_completion_time,
        'daily_stats': daily_stats,
        'weekly_max': weekly_max,
        'top_users': top_users,
        'weekly_tasks': weekly_tasks,
        'task_change': task_change,
        'completion_change': completion_change,
        'points_change': points_change,
        'title': 'Weekly Summary'
    })

def format_duration(seconds):
    """Format seconds into human readable duration"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds/60)}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{int(hours)}h {int(minutes)}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{int(days)}d {int(hours)}h"

@login_required
def upcoming_events(request):
    """Get upcoming events for sidebar"""
    today = timezone.now().date()
    next_week = today + timedelta(days=7)
    
    tasks = DailyTask.objects.filter(
        creator=request.user,
        date__range=[today, next_week],
        completed=False
    ).order_by('date', 'reminder_time')[:10]
    
    events = []
    for task in tasks:
        events.append({
            'id': task.id,
            'title': task.title,
            'date': task.date.strftime('%b %d'),
            'time': task.reminder_time.strftime('%I:%M %p') if task.reminder_time else 'All day'
        })
    
    return JsonResponse(events, safe=False)

@login_required
@require_POST
def notification_settings(request):
    """Save user's notification preferences"""
    data = json.loads(request.body)
    
    # In a real app, save this to UserProfile
    request.session['notifications_enabled'] = data.get('enabled', True)
    
    return JsonResponse({'success': True})

@login_required
def send_daily_digest(request):
    """Send daily digest email of today's tasks"""
    if request.method == 'POST':
        today = timezone.now().date()
        
        # Get today's tasks
        tasks = DailyTask.objects.filter(
            creator=request.user,
            date=today,
            completed=False
        ).order_by('reminder_time')
        
        # Prepare email content
        context = {
            'user': request.user,
            'tasks': tasks,
            'today': today,
            'task_count': tasks.count()
        }
        
        # Send email (implement your email sending logic)
        # send_daily_digest_email(request.user.email, context)
        
        return JsonResponse({
            'success': True,
            'message': f'Daily digest sent for {tasks.count()} tasks'
        })
    
    return JsonResponse({'success': False}, status=400)

@login_required
def get_weekly_stats(request):
    """API endpoint for weekly statistics"""
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Current week stats
    current_tasks = DailyTask.objects.filter(
        creator=request.user,
        date__range=[start_of_week, end_of_week]
    )
    
    # Last week stats for comparison
    last_start = start_of_week - timedelta(days=7)
    last_end = end_of_week - timedelta(days=7)
    last_tasks = DailyTask.objects.filter(
        creator=request.user,
        date__range=[last_start, last_end]
    )
    
    # Calculate stats
    current_total = current_tasks.count()
    last_total = last_tasks.count()
    
    current_completed = current_tasks.filter(completed=True).count()
    last_completed = last_tasks.filter(completed=True).count()
    
    current_points = sum(t.points for t in current_tasks.filter(completed=True))
    last_points = sum(t.points for t in last_tasks.filter(completed=True))
    
    # Calculate percentage changes
    task_change = ((current_total - last_total) / last_total * 100) if last_total > 0 else 0
    completion_change = ((current_completed - last_completed) / last_completed * 100) if last_completed > 0 else 0
    points_change = ((current_points - last_points) / last_points * 100) if last_points > 0 else 0
    
    return JsonResponse({
        'current_week': {
            'total_tasks': current_total,
            'completed': current_completed,
            'points': current_points,
            'completion_rate': (current_completed / current_total * 100) if current_total > 0 else 0
        },
        'changes': {
            'tasks': round(task_change, 1),
            'completion': round(completion_change, 1),
            'points': round(points_change, 1)
        }
    })

@login_required
def task_calendar(request):
    """Enhanced calendar view with event creation"""
    return render(request, 'tasks/calendar.html', {
        'title': 'Task Calendar',
        'today': timezone.now().date()
    })

@login_required
def calendar_events(request):
    """API endpoint for calendar events"""
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    try:
        start_date = datetime.fromisoformat(start)
        end_date = datetime.fromisoformat(end)
    except:
        start_date = timezone.now() - timedelta(days=30)
        end_date = timezone.now() + timedelta(days=30)
    
    # Get user's tasks
    tasks = DailyTask.objects.filter(
        creator=request.user,
        date__range=[start_date.date(), end_date.date()]
    )
    
    # Get group tasks where user is member
    member_tasks = DailyTask.objects.filter(
        taskmember__user=request.user,
        taskmember__status__in=['joined', 'completed'],
        date__range=[start_date.date(), end_date.date()]
    )
    
    all_tasks = tasks | member_tasks
    
    events = []
    for task in all_tasks.distinct():
        event_color = '#10b981' if task.completed else '#6d28d9'
        if task.date < timezone.now().date() and not task.completed:
            event_color = '#ef4444'  # Red for overdue
        
        events.append({
            'id': f'task_{task.id}',
            'title': task.title,
            'start': task.date.isoformat(),
            'end': task.date.isoformat(),
            'color': event_color,
            'extendedProps': {
                'type': 'task',
                'task_id': task.id,
                'completed': task.completed,
                'points': task.points,
                'description': task.description[:100],
                'reminder_time': task.reminder_time.strftime('%H:%M') if task.reminder_time else None,
                'is_group': task.group_task,
                'url': f'/tasks/{task.id}/'
            }
        })
    
    return JsonResponse(events, safe=False)

@login_required
@require_POST
def create_calendar_event(request):
    """Create task directly from calendar"""
    data = json.loads(request.body)
    
    form = DailyTaskForm({
        'title': data.get('title'),
        'description': data.get('description', ''),
        'date': data.get('date'),
        'reminder_time': data.get('reminder_time', '20:00'),
        'points': data.get('points', 10),
        'is_public': data.get('is_public', False),
        'group_task': data.get('group_task', False)
    })
    
    if form.is_valid():
        task = form.save(commit=False)
        task.creator = request.user
        task.save()
        
        # If it's a group task, add creator as member
        if task.group_task:
            TaskMember.objects.create(
                task=task,
                user=request.user,
                status='joined'
            )
        
        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'message': 'Task created successfully!'
        })
    
    return JsonResponse({
        'success': False,
        'errors': form.errors
    }, status=400)

@login_required
def update_calendar_event(request, task_id):
    """Update task from calendar drag & drop"""
    if request.method == 'POST':
        data = json.loads(request.body)
        task = get_object_or_404(DailyTask, id=task_id, creator=request.user)
        
        # Update date if changed (from drag & drop)
        if 'date' in data:
            task.date = data['date']
            task.reminder_sent = False  # Reset reminder for new date
            task.save()
            
            # Create a reminder record
            TaskReminder.objects.create(
                task=task,
                user=request.user,
                reminder_type='rescheduled'
            )
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def quick_create_event(request):
    """Quick event creation modal"""
    if request.method == 'POST':
        form = DailyTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.creator = request.user
            task.save()
            return JsonResponse({'success': True, 'task_id': task.id})
    
    return JsonResponse({'success': False}, status=400)