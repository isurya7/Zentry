from django.http import HttpResponse

# ------------------ TASK VIEWS ------------------

def create_task(request):
    return HttpResponse("Create a new task (public or private).")

def view_task(request, task_id):
    return HttpResponse(f"Viewing task with ID: {task_id}")

def edit_task(request, task_id):
    return HttpResponse(f"Editing task with ID: {task_id}")

def delete_task(request, task_id):
    return HttpResponse(f"Deleting task with ID: {task_id}")

def mark_task_complete(request, task_id):
    return HttpResponse(f"Marking task with ID {task_id} as complete.")

def invite_friends(request, task_id):
    return HttpResponse(f"Inviting friends to task with ID: {task_id}")

def task_calendar(request):
    return HttpResponse("Showing calendar with scheduled tasks.")

def weekly_summary(request):
    return HttpResponse("Showing weekly task summary and points.")
