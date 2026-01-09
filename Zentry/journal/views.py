from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from calendar import monthrange
from .models import JournalEntry, DiscoveredWord, PointTransaction
from .forms import JournalEntryForm
from .utils import extract_and_analyze_words, check_and_award_streak_bonus, deduct_journal_points
from accounts.models import UserProfile
from tasks.utils import check_streak_reminder, award_points
from notifications.models import Notification

@login_required
def journal_list(request):
    entries = JournalEntry.objects.filter(user=request.user).order_by('-date', '-created_at')
    
    mood_filter = request.GET.get('mood')
    if mood_filter:
        entries = entries.filter(mood=mood_filter)
    
    tag_filter = request.GET.get('tag')
    if tag_filter:
        entries = entries.filter(tags__icontains=tag_filter)
    
    public_count = entries.filter(is_public=True).count()
    entries_today = entries.filter(date=timezone.now().date()).count()
    
    # Get user profile for streak information
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Check streak reminder
    check_streak_reminder(request.user)
    
    # Calculate days until streak breaks (if no journal today)
    today = timezone.now().date()
    has_journal_today = JournalEntry.objects.filter(
        user=request.user,
        date=today
    ).exists()
    
    streak_warning = False
    if profile.current_streak > 0 and not has_journal_today:
        # Check if it's getting late (after 3 PM) - earlier warning
        from datetime import datetime
        current_hour = datetime.now().hour
        if current_hour >= 15:  # 3 PM - earlier reminder
            streak_warning = True
    
    # Get form for mood choices
    from .forms import JournalEntryForm
    form = JournalEntryForm()
    
    context = {
        'entries': entries,
        'mood_filter': mood_filter,
        'tag_filter': tag_filter,
        'public_count': public_count,
        'entries_today': entries_today,
        'profile': profile,
        'current_streak': profile.current_streak,
        'longest_streak': profile.longest_streak,
        'has_journal_today': has_journal_today,
        'streak_warning': streak_warning,
        'form': form,
    }
    return render(request, 'journal/journal_list.html', context)

@login_required
def create_journal_entry(request):
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.points_earned = 5  # Base 5 points for journal entry
            entry.word_points_earned = 0
            entry.streak_points_earned = 0
            
            # Save entry first to get ID
            entry.save()
            
            # Extract and analyze words from content
            discovered_words, word_points = extract_and_analyze_words(
                entry.content, 
                request.user, 
                entry
            )
            entry.word_points_earned = word_points
            entry.save()
            
            # Award points and update streak
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            today = timezone.now().date()
            
            # Calculate streak
            previous_streak = profile.current_streak
            streak_increased = False
            if profile.last_journal_date:
                days_diff = (today - profile.last_journal_date).days
                if days_diff == 1:
                    # Consecutive day
                    profile.current_streak += 1
                    streak_increased = True
                elif days_diff > 1:
                    # Streak broken
                    profile.current_streak = 1
                # If days_diff == 0, same day, don't change streak
            else:
                # First journal entry
                profile.current_streak = 1
                streak_increased = True
            
            if profile.current_streak > profile.longest_streak:
                profile.longest_streak = profile.current_streak
            
            # Check for streak milestone bonus (10, 20, 30, etc. days)
            streak_bonus = check_and_award_streak_bonus(request.user, profile.current_streak, previous_streak)
            entry.streak_points_earned = streak_bonus
            
            profile.last_journal_date = today
            
            # Calculate total points for this journal entry
            total_points = entry.get_total_points_earned()
            
            # Award points using the utility function
            award_points(request.user, total_points, activity_type='journal')
            
            # Create transaction records
            PointTransaction.objects.create(
                user=request.user,
                transaction_type='journal_entry',
                points=entry.points_earned,
                description=f"Created journal entry: {entry.title}",
                reference_id=entry.id,
            )
            
            if entry.streak_points_earned > 0:
                PointTransaction.objects.create(
                    user=request.user,
                    transaction_type='streak_milestone',
                    points=entry.streak_points_earned,
                    description=f"Reached {profile.current_streak}-day streak milestone",
                    reference_id=entry.id,
                )
            
            profile.save()
            
            # Create achievement post automatically
            try:
                from social.models import AchievementPost
                AchievementPost.objects.create(
                    user=request.user,
                    title=f"Journal Entry: {entry.title}",
                    content=f"I wrote a new journal entry '{entry.title}' and earned +{total_points} point{'s' if total_points != 1 else ''}! 📝",
                    achievement_type='journal',
                    points_earned=total_points,
                    is_public=entry.is_public
                )
            except:
                pass
            
            # Check streak reminders for future
            check_streak_reminder(request.user)
            
            points_message = f"Journal entry created successfully! Earned +{total_points} points"
            if word_points > 0:
                points_message += f" ({entry.points_earned} base + {word_points} from {word_points} word{'s' if word_points > 1 else ''})"
            if streak_bonus > 0:
                points_message += f" + {streak_bonus} streak bonus!"
            
            messages.success(request, points_message)
            return redirect('journal:journal_list')
    else:
        form = JournalEntryForm(initial={'date': timezone.now()})
    
    return render(request, 'journal/journal_form.html', {'form': form, 'title': 'Create Entry'})

@login_required
def view_journal_entry(request, entry_id):
    entry = get_object_or_404(JournalEntry, id=entry_id)
    
    if not entry.is_public and entry.user != request.user:
        messages.error(request, "You don't have permission to view this entry.")
        return redirect('journal:journal_list')
    
    # Get discovered words for this entry
    discovered_words = DiscoveredWord.objects.filter(
        journal_entry=entry,
        user=entry.user
    ).order_by('-created_at')
    
    return render(request, 'journal/journal_detail.html', {
        'entry': entry,
        'discovered_words': discovered_words,
        'total_points': entry.get_total_points_earned()
    })

@login_required
def edit_journal_entry(request, entry_id):
    entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
    
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, request.FILES, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, 'Journal entry updated successfully!')
            return redirect('journal:view_journal', entry_id=entry.id)
    else:
        form = JournalEntryForm(instance=entry)
    
    return render(request, 'journal/journal_form.html', {'form': form, 'title': 'Edit Entry'})

@login_required
def delete_journal_entry(request, entry_id):
    entry = get_object_or_404(JournalEntry, id=entry_id, user=request.user)
    
    if request.method == 'POST':
        # Deduct points before deleting
        points_deducted = deduct_journal_points(request.user, entry)
        
        entry.delete()
        
        if points_deducted > 0:
            messages.warning(request, f'Journal entry deleted. {points_deducted} points have been deducted from your total.')
        else:
            messages.success(request, 'Journal entry deleted successfully!')
        return redirect('journal:journal_list')
    
    return render(request, 'journal/journal_confirm_delete.html', {
        'entry': entry,
        'points_to_deduct': entry.get_total_points_earned()
    })

@login_required
def journal_calendar(request):
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    entries = JournalEntry.objects.filter(
        user=request.user,
        date__year=year,
        date__month=month
    )
    
    entries_by_date = {entry.date.day: entry for entry in entries}
    
    first_weekday, num_days = monthrange(year, month)
    
    days = []
    for day in range(1, num_days + 1):
        days.append(day)
    
    context = {
        'year': year,
        'month': month,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'entries_by_date': entries_by_date,
        'days': days,
        'first_weekday': first_weekday,
    }
    return render(request, 'journal/journal_calendar.html', context)

@login_required
def journal_search(request):
    query = request.GET.get('q', '')
    entries = JournalEntry.objects.filter(user=request.user)
    
    if query:
        entries = entries.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__icontains=query)
        )
    
    context = {
        'entries': entries,
        'query': query,
    }
    return render(request, 'journal/journal_search.html', context)

@login_required
def journal_by_tag(request, tag):
    entries = JournalEntry.objects.filter(
        user=request.user,
        tags__icontains=tag
    )
    
    context = {
        'entries': entries,
        'current_tag': tag,
    }
    return render(request, 'journal/journal_by_tag.html', context)

def public_journals(request):
    entries = JournalEntry.objects.filter(is_public=True).select_related('user')
    unique_authors = entries.values('user').distinct().count()
    
    context = {
        'entries': entries,
        'unique_authors': unique_authors,
    }
    return render(request, 'journal/public_journals.html', context)


@login_required
def points_history(request):
    """Display points transaction history"""
    transactions = PointTransaction.objects.filter(user=request.user).order_by('-created_at')[:100]
    
    # Calculate summary
    total_earned = PointTransaction.objects.filter(
        user=request.user,
        points__gt=0
    ).aggregate(total=Sum('points'))['total'] or 0
    
    total_deducted = abs(PointTransaction.objects.filter(
        user=request.user,
        points__lt=0
    ).aggregate(total=Sum('points'))['total'] or 0)
    
    # Group by type
    by_type = {}
    for trans in transactions:
        trans_type = trans.get_transaction_type_display()
        if trans_type not in by_type:
            by_type[trans_type] = {'count': 0, 'points': 0}
        by_type[trans_type]['count'] += 1
        by_type[trans_type]['points'] += trans.points
    
    context = {
        'transactions': transactions,
        'total_earned': total_earned,
        'total_deducted': total_deducted,
        'net_points': total_earned - total_deducted,
        'by_type': by_type,
        'title': 'Points History'
    }
    return render(request, 'journal/points_history.html', context)


@login_required
def discovered_words(request):
    """Display all discovered words with meanings"""
    words = DiscoveredWord.objects.filter(user=request.user).order_by('-discovered_date', '-created_at')
    
    # Statistics
    total_words = words.count()
    high_level_words = words.filter(is_high_level=True).count()
    total_word_points = words.aggregate(total=Sum('points_earned'))['total'] or 0
    
    context = {
        'words': words,
        'total_words': total_words,
        'high_level_words': high_level_words,
        'total_word_points': total_word_points,
        'title': 'Discovered Words'
    }
    return render(request, 'journal/discovered_words.html', context)


def points_guide(request):
    """Display points system guide"""
    guide_data = {
        'journal': {
            'title': 'Journal Entries',
            'items': [
                {'action': 'Create a journal entry', 'points': '+5 points', 'description': 'Base points for writing a journal entry'},
                {'action': 'Discover a high-level word', 'points': '+1 point per word', 'description': 'Find complex, uncommon words in your journal'},
                {'action': 'Maintain 10-day streak', 'points': '+20 points', 'description': 'Bonus for every 10 consecutive days of journaling'},
            ]
        },
        'tasks': {
            'title': 'Tasks',
            'items': [
                {'action': 'Complete a task', 'points': '+1 point', 'description': 'Base points for completing any task'},
            ]
        },
        'visions': {
            'title': 'Vision Boards',
            'items': [
                {'action': 'Achieve a vision board', 'points': '+20+ points', 'description': 'Points vary (minimum 20) based on vision board difficulty'},
            ]
        },
        'deductions': {
            'title': 'Point Deductions',
            'items': [
                {'action': 'Delete a journal entry', 'points': 'All points deducted', 'description': 'All points earned from that journal entry are deducted'},
            ]
        }
    }
    
    return render(request, 'journal/points_guide.html', {
        'guide_data': guide_data,
        'title': 'Points System Guide'
    })