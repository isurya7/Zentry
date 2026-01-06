from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from .models import Note
from .forms import NoteForm

@login_required
def create_note(request):
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            messages.success(request, 'Note created successfully!')
            return redirect('notes:view_note', note_id=note.id)
    else:
        form = NoteForm()
    
    context = {
        'form': form,
        'title': 'Create New Note'
    }
    return render(request, 'notes/create_note.html', context)

@login_required
def view_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    
    context = {
        'note': note,
        'title': note.title
    }
    return render(request, 'notes/view_note.html', context)

@login_required
def edit_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    
    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Note updated successfully!')
            return redirect('notes:view_note', note_id=note.id)
    else:
        form = NoteForm(instance=note)
    
    context = {
        'form': form,
        'note': note,
        'title': f'Edit: {note.title}'
    }
    return render(request, 'notes/edit_note.html', context)

@login_required
def delete_note(request, note_id):
    note = get_object_or_404(Note, id=note_id, user=request.user)
    
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted successfully!')
        return redirect('dashboard:dashboard')
    
    context = {
        'note': note,
        'title': 'Delete Note'
    }
    return render(request, 'notes/delete_note.html', context)

@login_required
def list_notes(request):
    notes = Note.objects.filter(user=request.user).order_by('-updated_at')
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        notes = notes.filter(title__icontains=search_query) | notes.filter(content__icontains=search_query)
    
    context = {
        'notes': notes,
        'search_query': search_query,
        'title': 'My Notes'
    }
    return render(request, 'notes/list_notes.html', context)