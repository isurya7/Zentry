from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    # Existing URLs
    path('create/', views.create_task, name='create_task'),
    path('<int:task_id>/', views.view_task, name='view_task'),
    path('<int:task_id>/edit/', views.edit_task, name='edit_task'),
    path('<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('<int:task_id>/complete/', views.mark_task_complete, name='complete_task'),
    path('<int:task_id>/invite/', views.invite_friends, name='invite_friends'),
    path('calendar/', views.task_calendar, name='task_calendar'),
    path('weekly-summary/', views.weekly_summary, name='weekly_summary'),
    
    # New URLs for reminder features
    path('dashboard/', views.task_dashboard, name='task_dashboard'),
    path('<int:task_id>/reminder/', views.set_reminder, name='set_reminder'),
    path('<int:task_id>/dismiss/<uuid:token>/', views.dismiss_reminder, name='dismiss_reminder'),
    path('<int:task_id>/test-reminder/', views.send_test_reminder, name='test_reminder'),

    # Calendar features
    path('calendar/events/', views.calendar_events, name='calendar_events'),
    path('create-calendar-event/', views.create_calendar_event, name='create_calendar_event'),
    path('<int:task_id>/update-event/', views.update_calendar_event, name='update_calendar_event'),
    path('quick-create/', views.quick_create_event, name='quick_create_event'),
    path('upcoming-events/', views.upcoming_events, name='upcoming_events'),
    path('notification-settings/', views.notification_settings, name='notification_settings'),
    path('send-daily-digest/', views.send_daily_digest, name='send_daily_digest'),
    path('weekly-stats/', views.get_weekly_stats, name='weekly_stats'),
    
    # API endpoints
    path('api/today/', views.api_tasks_today, name='api_tasks_today'),
    path('api/<int:task_id>/complete/', views.api_complete_task, name='api_complete_task'),
]