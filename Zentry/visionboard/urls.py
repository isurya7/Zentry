from django.urls import path
from . import views

app_name = 'visionboard'

urlpatterns = [
    path('', views.vision_list, name='vision_list'),
    path('create/', views.create_vision, name='create_vision'),
    path('<int:vision_id>/', views.view_vision, name='view_vision'),
    path('<int:vision_id>/edit/', views.edit_vision, name='edit_vision'),
    path('<int:vision_id>/checkpoint/add/', views.add_checkpoint, name='add_checkpoint'),
    path('checkpoint/<int:checkpoint_id>/complete/', views.mark_checkpoint_complete, name='mark_checkpoint_complete'),
    path('<int:vision_id>/achieve/', views.achieve_vision, name='achieve_vision'),
    path('<int:vision_id>/post/', views.post_to_feed, name='post_to_feed'),
]
