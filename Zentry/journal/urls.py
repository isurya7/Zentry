from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    path('', views.journal_list, name='journal_list'),
    path('create/', views.create_journal_entry, name='create_journal'),
    path('<int:entry_id>/', views.view_journal_entry, name='view_journal'),
    path('<int:entry_id>/edit/', views.edit_journal_entry, name='edit_journal'),
    path('<int:entry_id>/delete/', views.delete_journal_entry, name='delete_journal'),
    path('calendar/', views.journal_calendar, name='journal_calendar'),
    path('search/', views.journal_search, name='journal_search'),
    path('tags/<str:tag>/', views.journal_by_tag, name='journal_by_tag'),
    path('public/', views.public_journals, name='public_journals'),
    path('points/history/', views.points_history, name='points_history'),
    path('words/', views.discovered_words, name='discovered_words'),
    path('points/guide/', views.points_guide, name='points_guide'),
]