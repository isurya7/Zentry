from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_vision, name='create_vision'),
    path('<int:vision_id>/', views.view_vision, name='view_vision'),
    path('<int:vision_id>/edit/', views.edit_vision, name='edit_vision'),
    path('<int:vision_id>/delete/', views.delete_vision, name='delete_vision'),
    path('<int:vision_id>/react/', views.react_to_vision, name='react_vision'),
    path('<int:vision_id>/share/', views.share_vision, name='share_vision'),
    path('<int:vision_id>/achieve/', views.mark_as_achieved, name='achieve_vision'),
]
