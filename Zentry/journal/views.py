from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from calendar import monthrange
from .models import JournalEntry
from .forms import JournalEntryForm

@login_required
def journal_list(request):
    entries = JournalEntry.objects.filter(user=request.user)
    
    mood_filter = request.GET.get('mood')
    if mood_filter:
        entries = entries.filter(mood=mood_filter)
    
    tag_filter = request.GET.get('tag')
    if tag_filter:
        entries = entries.filter(tags__icontains=tag_filter)
    
    public_count = entries.filter(is_public=True).count()
    entries_today = entries.filter(date=timezone.now().date()).count()
    
    context = {
        'entries': entries,
        'mood_filter': mood_filter,
        'tag_filter': tag_filter,
        'public_count': public_count,
        'entries_today': entries_today,
    }
    return render(request, 'journal/journal_list.html', context)

@login_required
def create_journal_entry(request):
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            messages.success(request, 'Journal entry created successfully!')
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
    
    return render(request, 'journal/journal_detail.html', {'entry': entry})

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
        entry.delete()
        messages.success(request, 'Journal entry deleted successfully!')
        return redirect('journal:journal_list')
    
    return render(request, 'journal/journal_confirm_delete.html', {'entry': entry})

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