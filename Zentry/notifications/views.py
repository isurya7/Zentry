from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import Notification

@login_required
def notifications_list(request):
    """Get all notifications for user"""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-timestamp')[:50]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
        'unread_count': unread_count,
        'title': 'Notifications'
    })

@login_required
def get_notifications(request):
    """API endpoint to get notifications (for AJAX)"""
    notifications = Notification.objects.filter(recipient=request.user, is_read=False).order_by('-timestamp')[:10]
    
    notifications_data = [{
        'id': notif.id,
        'title': notif.title,
        'message': notif.message,
        'type': notif.notification_type or 'system',
        'link': notif.link or '',
        'timestamp': notif.timestamp.isoformat(),
    } for notif in notifications]
    
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return JsonResponse({
        'notifications': notifications_data,
        'unread_count': unread_count
    })

@login_required
def mark_read(request, notification_id):
    """Mark a notification as read"""
    notification = Notification.objects.get(id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    return JsonResponse({'success': True})

@login_required
def mark_all_read(request):
    """Mark all notifications as read"""
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(request, 'All notifications marked as read.')
        return redirect('notifications:list')
    return JsonResponse({'success': False}, status=400)
