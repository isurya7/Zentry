from django.http import HttpResponse

def create_vision(request):
    return HttpResponse("Create a new vision (image or text with caption).")

def view_vision(request, vision_id):
    return HttpResponse(f"Viewing vision post with ID: {vision_id}")

def edit_vision(request, vision_id):
    return HttpResponse(f"Editing vision post with ID: {vision_id}")

def delete_vision(request, vision_id):
    return HttpResponse(f"Deleting vision post with ID: {vision_id}")

def react_to_vision(request, vision_id):
    return HttpResponse(f"Reacting to vision post ID: {vision_id} if allowed by privacy.")

def share_vision(request, vision_id):
    return HttpResponse(f"Sharing vision post ID: {vision_id}")

def mark_as_achieved(request, vision_id):
    return HttpResponse(f"Marking vision post ID: {vision_id} as achieved with date.")
