from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_notifications, name='list_notifications'),
    path('<int:notif_id>/', views.view_notification, name='view_notification'),
    path('<int:notif_id>/mark-read/', views.mark_as_read, name='mark_notification_read'),
    path('<int:notif_id>/delete/', views.delete_notification, name='delete_notification'),
]
