from django.urls import path
from . import views

app_name = 'notes'

urlpatterns = [
    path('', views.list_notes, name='list_notes'),
    path('create/', views.create_note, name='create_note'),
    path('<int:note_id>/', views.view_note, name='view_note'),
    path('<int:note_id>/edit/', views.edit_note, name='edit_note'),
    path('<int:note_id>/delete/', views.delete_note, name='delete_note'),
]