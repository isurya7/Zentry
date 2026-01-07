from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.conversation_list, name='conversations'),
    path('conversation/<int:conversation_id>/', views.view_conversation, name='conversation'),
    path('start/<int:user_id>/', views.start_conversation, name='start_conversation'),
    path('conversation/<int:conversation_id>/send/', views.send_message, name='send_message'),
    path('conversation/<int:conversation_id>/messages/', views.get_messages, name='get_messages'),
]
