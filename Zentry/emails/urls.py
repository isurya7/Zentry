from django.urls import path
from . import views

app_name = 'emails'

urlpatterns = [
    path('connect/', views.connect_gmail, name="connect_gmail"),
    path('oauth2callback/', views.oauth2callback, name="oauth2callback"),
    path('inbox/', views.inbox_view, name="inbox"),
    path('refresh/', views.refresh_emails, name="refresh_emails"),
    path('email/<str:email_id>/', views.email_detail, name="email_detail"),
    path('reply/<str:email_id>/', views.reply_email, name="reply_email"),
    path('reply-success/', views.reply_success, name="reply_success"),
    path('resolve/<str:email_id>/', views.mark_resolved, name="mark_resolved"),
    path('disconnect/', views.disconnect_gmail, name="disconnect_gmail"),
]
