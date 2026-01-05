from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from accounts.models import UserProfile
@login_required
def dashboard(request):
    # Always try to fetch or create the user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Pass context to the template
    context = {
        'profile': profile,
        'stats': {
            'important_emails_week': 0,
            'important_emails_month': 0,
            'unread_emails_count': 0,
            'pending_tasks_count': 0,
            'completed_tasks_week': 0,
            'completed_tasks_month': 0,
            'journal_entries_week': 0,
        },
        'pending_tasks': [],
        'important_emails': [],
    }
    return render(request, 'dashboard/dashboard.html', context)