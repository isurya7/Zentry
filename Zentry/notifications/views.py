from django.http import HttpResponse

def list_notifications(request):
    return HttpResponse("Listing all notifications for the user.")

def view_notification(request, notif_id):
    return HttpResponse(f"Viewing notification with ID: {notif_id}")

def mark_as_read(request, notif_id):
    return HttpResponse(f"Marking notification ID {notif_id} as read.")

def delete_notification(request, notif_id):
    return HttpResponse(f"Deleting notification with ID: {notif_id}")
