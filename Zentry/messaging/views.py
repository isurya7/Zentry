from django.http import HttpResponse

def chat_rooms(request):
    return HttpResponse("Listing all chat rooms user is part of.")

def create_room(request):
    return HttpResponse("Create a new chat room.")

def view_room(request, room_id):
    return HttpResponse(f"Viewing messages in chat room ID: {room_id}")

def send_message(request, room_id):
    return HttpResponse(f"Sending message to room ID: {room_id}")

def join_room(request, room_id):
    return HttpResponse(f"Joining chat room ID: {room_id}")

def leave_room(request, room_id):
    return HttpResponse(f"Leaving chat room ID: {room_id}")
