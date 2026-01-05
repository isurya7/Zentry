from django.http import HttpResponse

def create_note(request):
    return HttpResponse("Creating a new note with bold heading.")

def view_note(request, note_id):
    return HttpResponse(f"Viewing note with ID: {note_id}")

def edit_note(request, note_id):
    return HttpResponse(f"Editing note with ID: {note_id}")

def delete_note(request, note_id):
    return HttpResponse(f"Deleting note with ID: {note_id}")
