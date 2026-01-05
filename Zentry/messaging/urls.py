from django.urls import path
from . import views

urlpatterns = [
    path('rooms/', views.chat_rooms, name='chat_rooms'),
    path('rooms/create/', views.create_room, name='create_room'),
    path('rooms/<int:room_id>/', views.view_room, name='view_room'),
    path('rooms/<int:room_id>/send/', views.send_message, name='send_message'),
    path('rooms/<int:room_id>/join/', views.join_room, name='join_room'),     # optional
    path('rooms/<int:room_id>/leave/', views.leave_room, name='leave_room'),  # optional
]
