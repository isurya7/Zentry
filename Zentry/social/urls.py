from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('feed/', views.feed, name='feed'),
    path('post/create/', views.create_achievement_post, name='create_post'),
    path('post/<int:post_id>/like/', views.like_post, name='like_post'),
    path('post/<int:post_id>/comment/', views.comment_post, name='comment_post'),
    path('report/<int:user_id>/', views.report_user, name='report_user'),
]

