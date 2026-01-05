from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_task, name='create_task'),
    path('<int:task_id>/', views.view_task, name='view_task'),
    path('<int:task_id>/edit/', views.edit_task, name='edit_task'),
    path('<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('<int:task_id>/complete/', views.mark_task_complete, name='complete_task'),
    path('<int:task_id>/invite/', views.invite_friends, name='invite_friends'),
    path('calendar/', views.task_calendar, name='task_calendar'),
    path('weekly-summary/', views.weekly_summary, name='weekly_summary'),
]
