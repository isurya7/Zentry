from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.landing_page, name='landing_page'),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('accounts/', include('accounts.urls')),
    path('emails/', include('emails.urls')),
    path('tasks/', include('tasks.urls')),
    path('notes/', include('notes.urls')),
    path('journal/', include('journal.urls', namespace='journal')),
    path('vision/', include('visionboard.urls')),
    path('notifications/', include('notifications.urls')),
    path('chat/', include('messaging.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

